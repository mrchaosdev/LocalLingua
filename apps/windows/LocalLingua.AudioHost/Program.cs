using System.Diagnostics;
using System.Net.WebSockets;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Buffers.Binary;
using System.Threading.Channels;
using NAudio.Wave;
using NAudio.CoreAudioApi;

using var stop = new CancellationTokenSource();
Console.CancelKeyPress += (_,e)=>{e.Cancel=true;stop.Cancel();};
string token=Environment.GetEnvironmentVariable("LOCALLINGUA_TOKEN")??throw new InvalidOperationException("Session token required");
using var http=new HttpClient { BaseAddress=new Uri("http://127.0.0.1:8765"), Timeout=TimeSpan.FromSeconds(2) };
http.DefaultRequestHeaders.Authorization=new AuthenticationHeaderValue("Bearer",token);
using var devices=new MMDeviceEnumerator();
CancellationTokenSource? captureStop=null;
Task? captureTask=null;
string activeKey="",lastError="";
long dropped=0;
uint activePid=0;
DateTime nextRetry=DateTime.MinValue,lastHeartbeat=DateTime.MinValue;
try {
    while (!stop.IsCancellationRequested) {
        try {
            using var document=JsonDocument.Parse(await http.GetStringAsync("/api/capture/config",stop.Token));
            var config=document.RootElement;
            string source=args.Contains("--system-diagnostic")?"system-diagnostic":config.GetProperty("source").GetString()!;
            string endpoint=config.GetProperty("endpoint_id").GetString()??"";
            uint pid=config.GetProperty("discord_pid").GetUInt32();
            string defaultId="";
            try { using var device=devices.GetDefaultAudioEndpoint(DataFlow.Render,Role.Multimedia); defaultId=device.ID; } catch { }
            string key=$"{source}|{endpoint}|{pid}|{defaultId}";
            bool enabled=config.GetProperty("mode").GetString()=="start";
            if (captureTask is not null && (!enabled || key!=activeKey || captureTask.IsCompleted)) {
                captureStop!.Cancel();
                try { await captureTask; } catch(OperationCanceledException) { } catch(Exception e) { lastError=e is FileNotFoundException?"native_helper_missing":e is EndOfStreamException?"discord_source_lost":"capture_restart_required"; }
                captureStop.Dispose();captureStop=null;captureTask=null;activeKey="";
                nextRetry=DateTime.UtcNow.AddSeconds(lastError.Length>0?2:0);
            }
            if (enabled && captureTask is null && DateTime.UtcNow>=nextRetry) {
                captureStop=CancellationTokenSource.CreateLinkedTokenSource(stop.Token);activeKey=key;lastError="";
                captureTask=source=="system-diagnostic"?CaptureSystem(endpoint,captureStop.Token):CaptureProcess(pid,captureStop.Token);
            }
            if ((DateTime.UtcNow-lastHeartbeat).TotalSeconds>=1) {
                var endpoints=new List<object>();
                try { foreach (var device in devices.EnumerateAudioEndPoints(DataFlow.Render,DeviceState.Active)) {
                    using (device) endpoints.Add(new {id=device.ID,name=device.FriendlyName});
                }} catch { }
                using var heartbeat=await http.PostAsJsonAsync("/api/capture/heartbeat",new {
                    state=captureTask is null?"idle":captureTask.IsCompleted?"reconnecting":"capturing",
                    code=lastError,pid=activePid,dropped=Interlocked.Read(ref dropped),devices=endpoints,processes=WindowsCatalog.DiscordRoots()
                },stop.Token);
                heartbeat.EnsureSuccessStatusCode();
                lastHeartbeat=DateTime.UtcNow;
            }
        } catch(OperationCanceledException) when(stop.IsCancellationRequested) { break; }
          catch(Exception) {
            if(captureStop is not null) captureStop.Cancel();
            lastError="engine_unavailable";
        }
        await Task.Delay(250,stop.Token);
    }
} catch(OperationCanceledException) { }
finally {
    captureStop?.Cancel();
    if(captureTask is not null) try { await captureTask; } catch { }
    captureStop?.Dispose();
}

long NowNs()=>(long)(Stopwatch.GetTimestamp()*(1_000_000_000.0/Stopwatch.Frequency));
async Task<ClientWebSocket> Connect(int rate,int channels,string format,string source,CancellationToken ct) {
    double best=double.MaxValue,offset=0;
    for(int i=0;i<3;i++) {
        double before=NowNs()/1e6;
        using var response=JsonDocument.Parse(await http.GetStringAsync("/api/clock",ct));
        double after=NowNs()/1e6,roundTrip=after-before;
        if(roundTrip<best) {best=roundTrip;offset=response.RootElement.GetProperty("mono_ms").GetDouble()-(before+after)/2;}
    }
    var ws=new ClientWebSocket();ws.Options.SetRequestHeader("Authorization","Bearer "+token);
    try {
        using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(5000);
        await ws.ConnectAsync(new Uri("ws://127.0.0.1:8765/ws/ingest"),timeout.Token);
        await ws.SendAsync(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new {
            type="audio.format",sample_rate=rate,channels,sample_format=format,source,protocol=2,
            clock_offset_ms=offset,clock_uncertainty_ms=best/2+(source=="system-diagnostic"?100:1)
        })),WebSocketMessageType.Text,true,ct);
        return ws;
    } catch {ws.Dispose();throw;}
}
async Task Send(ClientWebSocket ws,byte[] packet,CancellationToken ct) {
    using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(800);
    await ws.SendAsync(packet.AsMemory(),WebSocketMessageType.Binary,true,timeout.Token);
}
byte[] Frame(byte[] pcm,ulong sequence,ulong index,long endNs) {
    var bytes=new byte[40+pcm.Length];Encoding.ASCII.GetBytes("LLA2").CopyTo(bytes,0);
    BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(4),(uint)pcm.Length);
    BinaryPrimitives.WriteUInt64LittleEndian(bytes.AsSpan(8),sequence);
    BinaryPrimitives.WriteUInt64LittleEndian(bytes.AsSpan(16),index);
    BinaryPrimitives.WriteUInt64LittleEndian(bytes.AsSpan(24),(ulong)endNs);
    BinaryPrimitives.WriteUInt64LittleEndian(bytes.AsSpan(32),(ulong)Interlocked.Read(ref dropped));
    pcm.CopyTo(bytes,40);return bytes;
}
async Task CaptureProcess(uint pid,CancellationToken ct) {
    string helper=Path.Combine(AppContext.BaseDirectory,"LocalLingua.ProcessCapture.exe");
    if(!File.Exists(helper)) throw new FileNotFoundException("Native helper missing");
    using var native=Process.Start(new ProcessStartInfo(helper,pid.ToString()) {
        UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true
    })??throw new InvalidOperationException("Native helper failed");
    // Drain technical stderr without storing arbitrary strings or audio.
    var ready=new TaskCompletionSource<uint>(TaskCreationOptions.RunContinuationsAsynchronously);
    var drain=Task.Run(async()=>{
        while(await native.StandardError.ReadLineAsync(ct) is string line){
            const string prefix="Process-tree capture PID ";
            if(line.StartsWith(prefix)&&uint.TryParse(line[prefix.Length..].Split(';')[0],out var root))ready.TrySetResult(root);
        }
        ready.TrySetException(new EndOfStreamException("Native process did not become ready"));
    },ct);
    try {
        activePid=await ready.Task.WaitAsync(TimeSpan.FromSeconds(12),ct);
        using var ws=await Connect(44100,2,"pcm16","discord-process-tree",ct);
        var header=new byte[40];
        while(!ct.IsCancellationRequested) {
            await native.StandardOutput.BaseStream.ReadExactlyAsync(header,ct);
            if(Encoding.ASCII.GetString(header,0,4)!="LLA2") throw new InvalidDataException("Invalid native frame");
            int size=checked((int)BinaryPrimitives.ReadUInt32LittleEndian(header.AsSpan(4)));
            if(size<=0 || size>35280 || size%4!=0) throw new InvalidDataException("Invalid native PCM size");
            var packet=new byte[40+size];header.CopyTo(packet,0);
            await native.StandardOutput.BaseStream.ReadExactlyAsync(packet.AsMemory(40),ct);
            long endpoint=checked((long)BinaryPrimitives.ReadUInt64LittleEndian(header.AsSpan(24)));
            Interlocked.Exchange(ref dropped,(long)(BinaryPrimitives.ReadUInt64LittleEndian(header.AsSpan(32))&0x7fffffffffffffff));
            if(NowNs()-endpoint>800_000_000) {Interlocked.Increment(ref dropped);continue;}
            await Send(ws,packet,ct);
        }
    } finally {
        if(!native.HasExited) native.Kill(entireProcessTree:true);
        try {await drain;} catch(OperationCanceledException){}
        activePid=0;
    }
}
async Task CaptureSystem(string endpoint,CancellationToken ct) {
    activePid=0;
    using var device=endpoint.Length>0?devices.GetDevice(endpoint):devices.GetDefaultAudioEndpoint(DataFlow.Render,Role.Multimedia);
    using var capture=new WasapiLoopbackCapture(device);
    var fmt=capture.WaveFormat;
    bool isFloat=fmt.Encoding==WaveFormatEncoding.IeeeFloat || fmt is WaveFormatExtensible ext && ext.SubFormat==new Guid("00000003-0000-0010-8000-00aa00389b71");
    bool isPcm=fmt.Encoding==WaveFormatEncoding.Pcm || fmt is WaveFormatExtensible pcm && pcm.SubFormat==new Guid("00000001-0000-0010-8000-00aa00389b71");
    string encoding=isFloat&&fmt.BitsPerSample==32?"float32":isPcm&&fmt.BitsPerSample==16?"pcm16":throw new NotSupportedException("Unsupported PCM format");
    using var ws=await Connect(fmt.SampleRate,fmt.Channels,encoding,"system-diagnostic",ct);
    int frameBytes=fmt.SampleRate/25*fmt.BlockAlign;
    var queue=Channel.CreateBounded<byte[]>(new BoundedChannelOptions(20){FullMode=BoundedChannelFullMode.DropOldest,SingleReader=true,SingleWriter=true},_=>Interlocked.Increment(ref dropped));
    var pending=new byte[frameBytes];int used=0;ulong sequence=0,sampleIndex=0;
    capture.DataAvailable+=(_,e)=>{
        long callbackEnd=NowNs();int offset=0;
        while(offset<e.BytesRecorded) {
            int count=Math.Min(frameBytes-used,e.BytesRecorded-offset);
            Buffer.BlockCopy(e.Buffer,offset,pending,used,count);offset+=count;used+=count;
            if(used==frameBytes) {
                long frameEnd=callbackEnd-(long)((e.BytesRecorded-offset)/(double)fmt.AverageBytesPerSecond*1e9);
                queue.Writer.TryWrite(Frame(pending,sequence++,sampleIndex,frameEnd));
                sampleIndex+=(ulong)(frameBytes/fmt.BlockAlign);pending=new byte[frameBytes];used=0;
            }
        }
    };
    capture.RecordingStopped+=(_,e)=>queue.Writer.TryComplete(e.Exception);
    capture.StartRecording();
    try {await foreach(var packet in queue.Reader.ReadAllAsync(ct)) {
        long end=(long)BinaryPrimitives.ReadUInt64LittleEndian(packet.AsSpan(24));
        if(NowNs()-end>800_000_000) {Interlocked.Increment(ref dropped);continue;}
        await Send(ws,packet,ct);
    }} finally {capture.StopRecording();ws.Abort();}
}
