using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;
using System.Diagnostics;
using System.Net.Http;
using System.Net.Http.Headers;

namespace LocalLingua.Overlay;
public partial class MainWindow : Window {
    private readonly CancellationTokenSource _stop = new();
    private readonly Dictionary<string,int> _latest = new();
    private readonly HashSet<string> _final = new();
    private bool _simulated;
    private readonly Dictionary<string,long> _orders=new();
    private long _orderCounter,_displayOrder;
    private IntPtr _handle;
    private bool _locked,_canUnlock;
    private int _preferenceRevision=-1;
    private string _session="";
    public MainWindow() {
        InitializeComponent();
        SourceInitialized+=(_,_)=>{
            _handle=new WindowInteropHelper(this).Handle;
            _canUnlock=Desktop.RegisterHotKey(_handle,1,0x4003,0x4c);
            Desktop.RegisterHotKey(_handle,2,0x4003,0x4f);
            HwndSource.FromHwnd(_handle)?.AddHook(WindowMessage);
            Desktop.Restore(_handle);
        };
        Loaded += (_,_) => _ = ConnectLoopAsync();
        Closed += (_,_) => {_stop.Cancel();Desktop.ClickThrough(_handle,false);Desktop.Save(_handle);Desktop.UnregisterHotKey(_handle,1);Desktop.UnregisterHotKey(_handle,2);};
        PreviewKeyDown += (_, e) => {
            if (e.Key == Key.Escape) Close();
            if (e.Key == Key.Add || e.Key == Key.OemPlus) VietnameseText.FontSize = Math.Min(48, VietnameseText.FontSize + 2);
            if (e.Key == Key.Subtract || e.Key == Key.OemMinus) VietnameseText.FontSize = Math.Max(16, VietnameseText.FontSize - 2);
            if (e.Key == Key.Up && Keyboard.Modifiers.HasFlag(ModifierKeys.Control)) Opacity = Math.Min(1, Opacity + 0.05);
            if (e.Key == Key.Down && Keyboard.Modifiers.HasFlag(ModifierKeys.Control)) Opacity = Math.Max(0.35, Opacity - 0.05);
        };
    }
    private void Close_Click(object sender, RoutedEventArgs e) => Close();
    private void Monitor_Click(object sender,RoutedEventArgs e)=>Desktop.NextMonitor(_handle);
    private void Lock_Click(object sender,RoutedEventArgs e)=>ToggleLock();
    private void ToggleLock() {
        if(!_canUnlock){StatusText.Text="Không đăng ký được Ctrl+Alt+L; chưa khóa overlay.";return;}
        _locked=!_locked;Desktop.ClickThrough(_handle,_locked);LockButton.Content=_locked?"Ctrl+Alt+L: mở khóa":"Khóa";
    }
    private IntPtr WindowMessage(IntPtr hwnd,int message,IntPtr wParam,IntPtr lParam,ref bool handled) {
        if(message==Desktop.WmHotkey){if(wParam.ToInt32()==1)ToggleLock();else if(wParam.ToInt32()==2){if(IsVisible)Hide();else Show();}handled=true;}
        return IntPtr.Zero;
    }
    private void DragBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) {
        if (e.LeftButton == MouseButtonState.Pressed) DragMove();
    }
    private async Task ConnectLoopAsync() {
        while (!_stop.IsCancellationRequested) {
            using var socket = new ClientWebSocket();
            socket.Options.SetRequestHeader("Authorization", "Bearer " + Environment.GetEnvironmentVariable("LOCALLINGUA_TOKEN"));
            try {
                using var http=new HttpClient{Timeout=TimeSpan.FromSeconds(2)};
                http.DefaultRequestHeaders.Authorization=new AuthenticationHeaderValue("Bearer",Environment.GetEnvironmentVariable("LOCALLINGUA_TOKEN"));
                double offset=0,best=double.MaxValue;
                for(int i=0;i<3;i++){
                    double before=Stopwatch.GetTimestamp()*1000.0/Stopwatch.Frequency;
                    using var calibration=JsonDocument.Parse(await http.GetStringAsync("http://127.0.0.1:8765/api/clock",_stop.Token));
                    double after=Stopwatch.GetTimestamp()*1000.0/Stopwatch.Frequency;
                    if(after-before<best){best=after-before;offset=calibration.RootElement.GetProperty("mono_ms").GetDouble()-(before+after)/2;}
                }
                await socket.ConnectAsync(new Uri("ws://127.0.0.1:8765/ws/events"), _stop.Token);
                Dispatcher.Invoke(() => StatusText.Text = "● Connected · English → Vietnamese");
                var buffer = new byte[64 * 1024];
                using var json = new System.IO.MemoryStream();
                while (socket.State == WebSocketState.Open && !_stop.IsCancellationRequested) {
                    var r = await socket.ReceiveAsync(buffer, _stop.Token);
                    if (r.MessageType == WebSocketMessageType.Close) break;
                    if (r.MessageType != WebSocketMessageType.Text) continue;
                    json.Write(buffer,0,r.Count);
                    if (json.Length > 262144) throw new InvalidOperationException("Event too large");
                    if (!r.EndOfMessage) continue;
                    string message = Encoding.UTF8.GetString(json.ToArray()); json.SetLength(0);
                    using var doc = JsonDocument.Parse(message);
                    var root=doc.RootElement;
                    if (!root.TryGetProperty("type",out var typ)) continue;
                    if (typ.GetString()=="caption") {
                        string phase=root.GetProperty("phase").GetString()??"";
                        string id=root.GetProperty("utterance_id").GetString()??"";
                        bool translation=phase.StartsWith("translation");
                        string key=id+(translation?":vi":":en");
                        int revision=root.GetProperty("revision").GetInt32();
                        if(_final.Contains(key)||_latest.TryGetValue(key,out var seen)&&revision<=seen)continue;
                        _latest[key]=revision;
                        if(phase.EndsWith("final"))_final.Add(key);
                        if(!_orders.TryGetValue(id,out var order)){order=++_orderCounter;_orders[id]=order;}
                        while(_orders.Count>140){
                            string oldest=_orders.Keys.First();_orders.Remove(oldest);
                            foreach(string suffix in new[]{":en",":vi"}){_latest.Remove(oldest+suffix);_final.Remove(oldest+suffix);}
                        }
                        if(order<_displayOrder)continue;
                        bool next=order>_displayOrder;_displayOrder=order;
                        string en=root.GetProperty("english").GetString()??"";
                        string vi=root.GetProperty("vietnamese").GetString()??"";
                        string source=root.GetProperty("source").GetString()??"";
                        _simulated=source is "demo" or "mock";
                        Dispatcher.Invoke(()=>{
                            EnglishText.Text=en;
                            if(translation)VietnameseText.Text=vi;
                            else if(next)VietnameseText.Text="Đang chờ bản dịch tiếng Việt…";
                            StatusText.Text=(translation?(phase.EndsWith("final")?"● Bản dịch hoàn chỉnh":"◌ Đang dịch · Có thể thay đổi"):"◌ Đã nhận tiếng Anh · Đang dịch")+(_simulated?" · MÔ PHỎNG":"");
                        });
                        if(root.TryGetProperty("trace_id",out var trace)&&root.TryGetProperty("clock_calibrated",out var calibrated)&&calibrated.GetBoolean()){
                            await Dispatcher.InvokeAsync(()=>{},DispatcherPriority.Render);
                            var ack=JsonSerializer.Serialize(new{type="render.ack",trace_id=trace.GetString(),render_mono_ms=Stopwatch.GetTimestamp()*1000.0/Stopwatch.Frequency+offset,uncertainty_ms=best/2+16});
                            await socket.SendAsync(Encoding.UTF8.GetBytes(ack),WebSocketMessageType.Text,true,_stop.Token);
                        }
                    } else if (typ.GetString()=="status") {
                        string session=root.GetProperty("session_id").GetString()??"";
                        if(session!=_session){_latest.Clear();_final.Clear();_orders.Clear();_displayOrder=0;_orderCounter=0;_session=session;_preferenceRevision=-1;}
                        if(root.TryGetProperty("preference_revision",out var revision)&&revision.GetInt32()!=_preferenceRevision){
                            _preferenceRevision=revision.GetInt32();var p=root.GetProperty("preferences");
                            Dispatcher.Invoke(()=>{VietnameseText.FontSize=p.GetProperty("overlay_font_size").GetDouble();Opacity=p.GetProperty("overlay_opacity").GetDouble();EnglishText.Visibility=p.GetProperty("overlay_english").GetBoolean()?Visibility.Visible:Visibility.Collapsed;});
                        }
                        string mode=root.GetProperty("mode").GetString() ?? "stop";
                        bool capturing=root.GetProperty("capture_connected").GetBoolean();
                        Dispatcher.Invoke(()=>StatusText.Text=(mode=="start"?(capturing?"● Đang thu audio · EN → VI":"◌ Đang chờ nguồn audio"):capturing?"◌ Đang dừng nguồn audio":mode=="pause"?"◌ Tạm dừng":"○ Đã dừng")+(_simulated?" · MÔ PHỎNG":""));
                    } else if (typ.GetString()=="error") {
                        string err=root.TryGetProperty("message",out var m)?m.GetString()??"unknown":"unknown";
                        Dispatcher.Invoke(()=>StatusText.Text="⚠ " + err);
                    }
                }
                Dispatcher.Invoke(()=>StatusText.Text="○ Mất kết nối engine · Phụ đề đã cũ");
            } catch(OperationCanceledException) { break; }
              catch(Exception ex) { Dispatcher.Invoke(()=>StatusText.Text="○ Engine disconnected: "+ex.GetType().Name); }
            try { await Task.Delay(1750,_stop.Token); } catch(OperationCanceledException) { break; }
        }
    }
}
