using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using NAudio.Wave;

// DIAGNOSTIC ONLY: Captures all audio from default output device, NOT Discord-only.
// True Discord process-specific capture must be implemented in milestone M2.
Console.WriteLine("LocalLingua AudioHost — WHOLE SYSTEM LOOPBACK DIAGNOSTIC");
Console.WriteLine("WARNING: Will include audio from all apps on default output. Do not use with confidential content.");
using var ws = new ClientWebSocket();
using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

var uri = new Uri("ws://127.0.0.1:8765/ws/ingest");
try { await ws.ConnectAsync(uri, cts.Token); }
catch (Exception ex) { Console.Error.WriteLine("Backend connection failed: " + ex.Message); return; }

using var capture = new WasapiLoopbackCapture();
// NAudio WASAPI output normally uses IEEE float32, but verify the negotiated mix format.
var sampleFormat = capture.WaveFormat.Encoding switch {
    WaveFormatEncoding.IeeeFloat when capture.WaveFormat.BitsPerSample == 32 => "float32",
    WaveFormatEncoding.Pcm when capture.WaveFormat.BitsPerSample == 16 => "pcm16",
    _ => throw new NotSupportedException($"Unsupported endpoint format {capture.WaveFormat}")
};
Console.WriteLine($"Capture device format: {capture.WaveFormat}");
var hello = JsonSerializer.Serialize(new {
    type = "audio.format", sample_rate = capture.WaveFormat.SampleRate,
    channels = capture.WaveFormat.Channels, sample_format = sampleFormat
});
await ws.SendAsync(Encoding.UTF8.GetBytes(hello), WebSocketMessageType.Text, true, cts.Token);

var frames = Channel.CreateBounded<byte[]>(new BoundedChannelOptions(64) {
    FullMode = BoundedChannelFullMode.DropOldest,
    SingleReader = true, SingleWriter = false
});
int droppedApprox = 0;
capture.DataAvailable += (_, args) => {
    // No I/O, ML inference or await in WASAPI audio callback.
    var chunk = new byte[args.BytesRecorded];
    Buffer.BlockCopy(args.Buffer, 0, chunk, 0, args.BytesRecorded);
    if (!frames.Writer.TryWrite(chunk)) Interlocked.Increment(ref droppedApprox);
};
capture.RecordingStopped += (_, args) => {
    if (args.Exception is not null) Console.Error.WriteLine(args.Exception);
    frames.Writer.TryComplete();
};
capture.StartRecording();
Console.WriteLine("Capturing output audio. Press Ctrl+C to exit. Start backend UI listening before expecting captions.");
try {
    await foreach (var data in frames.Reader.ReadAllAsync(cts.Token)) {
        if (ws.State != WebSocketState.Open) break;
        await ws.SendAsync(data, WebSocketMessageType.Binary, true, cts.Token);
    }
} catch (OperationCanceledException) { }
  catch (WebSocketException ex) { Console.Error.WriteLine("Backend WS lost: " + ex.Message); }
finally {
    capture.StopRecording();
    Console.WriteLine($"Stopped; approximate channel writes dropped: {droppedApprox}. NOTE: DropOldest evictions require separate counters in M3.");
    if (ws.State == WebSocketState.Open) {
        try { await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "stop", CancellationToken.None); } catch { }
    }
}
