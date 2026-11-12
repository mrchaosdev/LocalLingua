using System.Diagnostics;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Drawing;
using System.Windows.Forms;

namespace LocalLingua.Launcher;
static class Program {
    [STAThread]
    static void Main() {
        using var instance = new Mutex(true, "LocalLingua.Personal.Launcher", out bool created);
        if (!created) { MessageBox.Show("LocalLingua đang chạy trong khay hệ thống."); return; }
        ApplicationConfiguration.Initialize();
        try { Application.Run(new Supervisor()); }
        catch (Exception e) { MessageBox.Show("Không khởi động được LocalLingua: " + e.Message); }
    }
}
sealed class Supervisor : ApplicationContext {
    readonly string root = AppContext.BaseDirectory;
    readonly string token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
    readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(2) };
    readonly NotifyIcon tray;
    readonly System.Windows.Forms.Timer timer = new() { Interval = 2000 };
    readonly Dictionary<string, Process> children = new();
    readonly Dictionary<string, int> retries = new();
    bool checking, closing;
    public Supervisor() {
        http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer",token);
        var menu = new ContextMenuStrip();
        menu.Items.Add("Mở bảng phụ đề", null, (_,_) => OpenDashboard());
        menu.Items.Add("Mở overlay", null, (_,_) => {retries["LocalLingua.Overlay.exe"]=0;Ensure("LocalLingua.Overlay.exe");});
        menu.Items.Add("Thử khởi động lại thành phần lỗi",null,(_,_)=>retries.Clear());
        menu.Items.Add("Cài Ollama (trang chính thức)",null,(_,_)=>Process.Start(new ProcessStartInfo("https://ollama.com/download/windows"){UseShellExecute=true}));
        menu.Items.Add("Thoát LocalLingua", null, async (_,_) => await Shutdown());
        tray = new NotifyIcon { Icon = SystemIcons.Application, Text = "LocalLingua · Đang khởi động", ContextMenuStrip = menu, Visible = true };
        tray.DoubleClick += (_,_) => OpenDashboard();
        timer.Tick += async (_,_) => await Tick();
        Ensure("engine/LocalLingua.Engine.exe");
        timer.Start();
    }
    void Ensure(string relative) {
        if (closing) return;
        if (retries.GetValueOrDefault(relative) > 5) return;
        if (children.TryGetValue(relative, out var previous)) {
            if (!previous.HasExited) return;
            TechnicalLog.Write(relative,"process_exited",previous.ExitCode);
            previous.Dispose(); children.Remove(relative);
            retries[relative] = retries.GetValueOrDefault(relative) + 1;
            if (retries[relative] > 5) { tray.Text = "LocalLingua · Lỗi khởi động, kiểm tra cấu hình"; return; }
        }
        string file = Path.Combine(root, relative);
        if (!File.Exists(file)) throw new FileNotFoundException("Thiếu thành phần ứng dụng",relative);
        var start = new ProcessStartInfo(file) { WorkingDirectory = Path.GetDirectoryName(file)!, UseShellExecute = false, CreateNoWindow = true };
        start.Environment["LOCALLINGUA_TOKEN"] = token;
        start.Environment["LOCALLINGUA_WEB_DIR"] = Path.Combine(root,"web");
        start.Environment["LOCALLINGUA_DATA_DIR"] = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalLingua");
        children[relative] = Process.Start(start) ?? throw new InvalidOperationException("Cannot launch " + relative);
    }
    bool opened;
    async Task Tick() {
        if (checking || closing) return;
        checking = true;
        try {
            Ensure("engine/LocalLingua.Engine.exe");
            using var response = await http.GetAsync("http://127.0.0.1:8765/api/status");
            if(closing)return;
            if (!response.IsSuccessStatusCode) { tray.Text = "LocalLingua · Cổng 8765 bị chiếm hoặc sai phiên"; return; }
            Ensure("LocalLingua.AudioHost.exe");
            if (!opened) { Ensure("LocalLingua.Overlay.exe"); OpenDashboard(); opened=true; }
            else if(children.TryGetValue("LocalLingua.Overlay.exe",out var overlay)&&overlay.HasExited&&overlay.ExitCode!=0)Ensure("LocalLingua.Overlay.exe");
            using var status = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            var state=status.RootElement;
            if(state.GetProperty("translate_backend").GetString()=="ollama"||state.GetProperty("model_install").GetProperty("state").GetString()=="running")await EnsureOllama();
            if(closing)return;
            tray.Text=state.GetProperty("mode").GetString()!="start"?"LocalLingua · Đã dừng thu audio":
                state.GetProperty("capture_connected").GetBoolean()?"LocalLingua · Đang thu audio và dịch EN → VI":"LocalLingua · Đang chờ nguồn Discord";
        } catch { if(!closing)tray.Text = "LocalLingua · Chưa kết nối được engine"; }
        finally { checking=false; }
    }
    void OpenDashboard() => Process.Start(new ProcessStartInfo("http://127.0.0.1:8765/#token=" + token) { UseShellExecute=true });
    async Task EnsureOllama() {
        if(closing)return;
        using var local=new HttpClient{Timeout=TimeSpan.FromSeconds(1)};
        try{using var version=await local.GetAsync("http://127.0.0.1:11434/api/version");if(version.IsSuccessStatusCode)return;}catch(HttpRequestException){}catch(TaskCanceledException){}
        const string key="owned-ollama";
        if(closing)return;
        if(children.TryGetValue(key,out var previous)){
            if(!previous.HasExited)return;
            TechnicalLog.Write("owned-ollama","process_exited",previous.ExitCode);
            previous.Dispose();children.Remove(key);retries[key]=retries.GetValueOrDefault(key)+1;
        }
        if(retries.GetValueOrDefault(key)>5)return;
        var paths=(Environment.GetEnvironmentVariable("PATH")??"").Split(Path.PathSeparator)
            .Append(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","Ollama"));
        string? binary=paths.Select(p=>Path.Combine(p,"ollama.exe")).FirstOrDefault(File.Exists);
        if(binary is null)return;
        var start=new ProcessStartInfo(binary,"serve"){UseShellExecute=false,CreateNoWindow=true};
        start.Environment["OLLAMA_HOST"]="127.0.0.1:11434";
        start.Environment["OLLAMA_NO_CLOUD"]="1";
        var process=Process.Start(start);if(process is not null)children[key]=process;
    }
    async Task Shutdown() {
        if (closing) return;
        closing=true; timer.Stop();
        try { await http.PostAsync("http://127.0.0.1:8765/api/shutdown",new StringContent("{}")); } catch { }
        await Task.Delay(5000);
        foreach (var child in children.Values) { try { if (!child.HasExited) child.Kill(entireProcessTree:true); child.Dispose(); } catch { } }
        tray.Visible=false; tray.Dispose(); http.Dispose(); timer.Dispose(); ExitThread();
    }
}
