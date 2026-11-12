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
        menu.Items.Add("Mở overlay", null, (_,_) => Ensure("LocalLingua.Overlay.exe"));
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
            previous.Dispose(); children.Remove(relative);
            retries[relative] = retries.GetValueOrDefault(relative) + 1;
            if (retries[relative] > 5) { tray.Text = "LocalLingua · Lỗi khởi động, kiểm tra cấu hình"; return; }
        }
        string file = Path.Combine(root, relative);
        if (!File.Exists(file)) throw new FileNotFoundException("Thiếu thành phần ứng dụng",relative);
        var start = new ProcessStartInfo(file) { WorkingDirectory = Path.GetDirectoryName(file)!, UseShellExecute = false, CreateNoWindow = true };
        start.Environment["LOCALLINGUA_TOKEN"] = token;
        start.Environment["LOCALLINGUA_WEB_DIR"] = Path.Combine(root,"web");
        children[relative] = Process.Start(start) ?? throw new InvalidOperationException("Cannot launch " + relative);
    }
    bool opened;
    async Task Tick() {
        if (checking || closing) return;
        checking = true;
        try {
            Ensure("engine/LocalLingua.Engine.exe");
            var response = await http.GetAsync("http://127.0.0.1:8765/api/status");
            if (!response.IsSuccessStatusCode) { tray.Text = "LocalLingua · Cổng 8765 bị chiếm hoặc sai phiên"; return; }
            Ensure("LocalLingua.AudioHost.exe");
            if (!opened) { Ensure("LocalLingua.Overlay.exe"); OpenDashboard(); opened=true; }
            using var status = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            tray.Text = status.RootElement.GetProperty("capture_connected").GetBoolean()
                ? "LocalLingua · Nguồn audio kết nối; điều khiển trên dashboard"
                : "LocalLingua · Chưa có nguồn Discord; kiểm tra Discord";
        } catch { tray.Text = "LocalLingua · Chưa kết nối được engine"; }
        finally { checking=false; }
    }
    void OpenDashboard() => Process.Start(new ProcessStartInfo("http://127.0.0.1:8765/#token=" + token) { UseShellExecute=true });
    async Task Shutdown() {
        if (closing) return;
        closing=true; timer.Stop();
        try { await http.PostAsync("http://127.0.0.1:8765/api/shutdown",new StringContent("{}")); } catch { }
        await Task.Delay(5000);
        foreach (var child in children.Values) { try { if (!child.HasExited) child.Kill(entireProcessTree:true); child.Dispose(); } catch { } }
        tray.Visible=false; tray.Dispose(); http.Dispose(); timer.Dispose(); ExitThread();
    }
}
