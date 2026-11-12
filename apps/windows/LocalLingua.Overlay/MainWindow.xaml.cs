using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Input;

namespace LocalLingua.Overlay;
public partial class MainWindow : Window {
    private readonly CancellationTokenSource _stop = new();
    private readonly Dictionary<string,int> _latest = new();
    public MainWindow() {
        InitializeComponent();
        Loaded += (_,_) => _ = ConnectLoopAsync();
        Closed += (_,_) => _stop.Cancel();
    }
    private void Close_Click(object sender, RoutedEventArgs e) => Close();
    private void DragBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) {
        if (e.LeftButton == MouseButtonState.Pressed) DragMove();
    }
    private async Task ConnectLoopAsync() {
        while (!_stop.IsCancellationRequested) {
            using var socket = new ClientWebSocket();
            try {
                await socket.ConnectAsync(new Uri("ws://127.0.0.1:8765/ws/events"), _stop.Token);
                Dispatcher.Invoke(() => StatusText.Text = "● Connected · English → Vietnamese");
                var buffer = new byte[64 * 1024];
                var json = new StringBuilder();
                while (socket.State == WebSocketState.Open && !_stop.IsCancellationRequested) {
                    var r = await socket.ReceiveAsync(buffer, _stop.Token);
                    if (r.MessageType == WebSocketMessageType.Close) break;
                    if (r.MessageType != WebSocketMessageType.Text) continue;
                    json.Append(Encoding.UTF8.GetString(buffer,0,r.Count));
                    if (!r.EndOfMessage) continue;
                    string message = json.ToString(); json.Clear();
                    using var doc = JsonDocument.Parse(message);
                    var root=doc.RootElement;
                    if (!root.TryGetProperty("type",out var typ)) continue;
                    if (typ.GetString()=="caption") {
                        string phase=root.GetProperty("phase").GetString() ?? "";
                        if (!phase.StartsWith("translation")) continue;
                        string id=root.GetProperty("utterance_id").GetString() ?? "";
                        int revision=root.GetProperty("revision").GetInt32();
                        if (_latest.TryGetValue(id,out var seen) && revision<=seen) continue;
                        _latest[id]=revision;
                        string vi=root.GetProperty("vietnamese").GetString() ?? "";
                        string en=root.GetProperty("english").GetString() ?? "";
                        Dispatcher.Invoke(()=>{
                            VietnameseText.Text=vi;EnglishText.Text=en;
                            StatusText.Text=phase.EndsWith("final")?"● Translation · Final":"◌ Đang dịch · Tentative";
                        });
                    } else if (typ.GetString()=="error") {
                        string err=root.TryGetProperty("message",out var m)?m.GetString()??"unknown":"unknown";
                        Dispatcher.Invoke(()=>StatusText.Text="⚠ " + err);
                    }
                }
            } catch(OperationCanceledException) { break; }
              catch(Exception ex) { Dispatcher.Invoke(()=>StatusText.Text="○ Engine disconnected: "+ex.GetType().Name); }
            try { await Task.Delay(1750,_stop.Token); } catch(OperationCanceledException) { break; }
        }
    }
}
