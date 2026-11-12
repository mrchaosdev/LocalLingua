using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using NAudio.Wave;

using var stop = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; stop.Cancel(); };
var token = Environment.GetEnvironmentVariable("LOCALLINGUA_TOKEN") ?? "";
Console.WriteLine("LocalLingua: WHOLE SYSTEM diagnostic. Includes every application on default output.");
while (!stop.IsCancellationRequested) {
    try { await Capture(stop.Token); }
    catch (OperationCanceledException) when (stop.IsCancellationRequested) { break; }
    catch (Exception e) { Console.Error.WriteLine($"Capture disconnected: {e.GetType().Name}. Retrying."); }
    try { await Task.Delay(2000, stop.Token); } catch (OperationCanceledException) { break; }
}

async Task Capture(CancellationToken ct) {
    using var ws = new ClientWebSocket();
    ws.Options.SetRequestHeader("Authorization", "Bearer " + token);
    using var connect = CancellationTokenSource.CreateLinkedTokenSource(ct);
    connect.CancelAfter(TimeSpan.FromSeconds(5));
    await ws.ConnectAsync(new Uri("ws://127.0.0.1:8765/ws/ingest"), connect.Token);
    using var capture = new WasapiLoopbackCapture();
    var fmt = capture.WaveFormat;
    // WASAPI commonly negotiates WAVEFORMATEXTENSIBLE rather than plain IEEE_FLOAT.
    bool isFloat = fmt.Encoding == WaveFormatEncoding.IeeeFloat ||
        fmt is WaveFormatExtensible ext && ext.SubFormat == new Guid("00000003-0000-0010-8000-00aa00389b71");
    string encoding = isFloat && fmt.BitsPerSample == 32 ? "float32" :
        fmt.BitsPerSample == 16 && (fmt.Encoding == WaveFormatEncoding.Pcm ||
        fmt is WaveFormatExtensible pcm && pcm.SubFormat == new Guid("00000001-0000-0010-8000-00aa00389b71")) ? "pcm16" :
        throw new NotSupportedException($"Unsupported format: {fmt}");
    await ws.SendAsync(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new {
        type = "audio.format", sample_rate = fmt.SampleRate, channels = fmt.Channels,
        sample_format = encoding, source = "system-diagnostic"
    })), WebSocketMessageType.Text, true, ct);
    long drops = 0;
    int frameBytes = fmt.SampleRate / 25 * fmt.BlockAlign; // 40ms
    var frames = Channel.CreateBounded<(byte[] Data, long Time)>(new BoundedChannelOptions(20) {
        FullMode = BoundedChannelFullMode.DropOldest, SingleReader = true, SingleWriter = true
    }, _ => Interlocked.Increment(ref drops));
    var pending = new byte[frameBytes];
    int used = 0;
    capture.DataAvailable += (_, e) => {
        int offset = 0;
        while (offset < e.BytesRecorded) {
            int count = Math.Min(frameBytes - used, e.BytesRecorded - offset);
            Buffer.BlockCopy(e.Buffer, offset, pending, used, count);
            offset += count; used += count;
            if (used == frameBytes) {
                frames.Writer.TryWrite((pending, Stopwatch.GetTimestamp()));
                pending = new byte[frameBytes]; used = 0;
            }
        }
    };
    capture.RecordingStopped += (_, e) => frames.Writer.TryComplete(e.Exception);
    capture.StartRecording();
    try {
        await foreach (var frame in frames.Reader.ReadAllAsync(ct)) {
            if (Stopwatch.GetElapsedTime(frame.Time).TotalMilliseconds > 800) {
                Interlocked.Increment(ref drops); continue;
            }
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(ct);
            deadline.CancelAfter(TimeSpan.FromSeconds(2));
            await ws.SendAsync(frame.Data, WebSocketMessageType.Binary, true, deadline.Token);
        }
    } finally {
        capture.StopRecording();
        Console.WriteLine($"Dropped capture frames: {drops}");
        ws.Abort();
    }
}
