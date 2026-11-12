// LocalLingua process-tree loopback. API reference: Microsoft ApplicationLoopback sample.
// Framed 44100 Hz stereo PCM16 stdout; metadata-only stderr. No audio files.
#include <windows.h>
#include <tlhelp32.h>
#include <audioclient.h>
#include <audioclientactivationparams.h>
#include <mmdeviceapi.h>
#include <wrl.h>
#include <io.h>
#include <fcntl.h>
#include <cstdio>
#include <deque>
#include <map>
#include <vector>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <atomic>
#include <stdexcept>
#include <string>
#include <cstring>
#include <cstdint>
#include <chrono>
using namespace Microsoft::WRL;
void check(HRESULT hr) { if (FAILED(hr)) { fprintf(stderr,"HRESULT 0x%08lX\n",hr); throw std::runtime_error("Windows audio API failed"); } }
struct Header { char magic[4]={'L','L','A','2'}; uint32_t size=0; uint64_t sequence=0,index=0,endNs=0,dropped=0; };
static_assert(sizeof(Header)==40);
struct Packet { Header header; std::vector<BYTE> bytes; };

DWORD discordRoot(DWORD requested) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot enumerate processes");
    std::map<DWORD, DWORD> parents;
    PROCESSENTRY32W p{}; p.dwSize = sizeof(p);
    if (Process32FirstW(snap, &p)) do {
        if (_wcsicmp(p.szExeFile, L"Discord.exe") == 0) parents[p.th32ProcessID] = p.th32ParentProcessID;
    } while (Process32NextW(snap, &p));
    CloseHandle(snap);
    if (requested) {
        if (parents.contains(requested) && parents.contains(parents[requested]))
            throw std::runtime_error("Selected PID is not a Discord root; refresh process selection");
        if (parents.contains(requested)) return requested;
        // A restarted Discord gets a new PID. Rebind only if the root is unambiguous.
    }
    DWORD root = 0;
    for (auto [id, parent] : parents) if (!parents.contains(parent)) {
        if (root) throw std::runtime_error("Multiple Discord roots; close additional instances");
        root = id;
    }
    if (!root) throw std::runtime_error("Discord is not running");
    return root;
}

class Activation : public RuntimeClass<RuntimeClassFlags<ClassicCom>, FtmBase, IActivateAudioInterfaceCompletionHandler> {
public:
    HANDLE done = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    HRESULT result = E_PENDING;
    ComPtr<IAudioClient> client;
    ~Activation() { CloseHandle(done); }
    STDMETHOD(ActivateCompleted)(IActivateAudioInterfaceAsyncOperation* op) override {
        ComPtr<IUnknown> unknown;
        HRESULT activation = E_FAIL;
        result = op->GetActivateResult(&activation, &unknown);
        if (SUCCEEDED(result)) result = activation;
        if (SUCCEEDED(result)) result = unknown.As(&client);
        SetEvent(done);
        return S_OK;
    }
};

int main(int argc,char** argv) {
    _setmode(_fileno(stdout), _O_BINARY);
    try {
        check(CoInitializeEx(nullptr, COINIT_MULTITHREADED));
        DWORD pid = discordRoot(argc>1?static_cast<DWORD>(std::stoul(argv[1])):0);
        HANDLE process = OpenProcess(SYNCHRONIZE, FALSE, pid);
        if (!process) throw std::runtime_error("Cannot monitor Discord process");
        auto activation = Make<Activation>();
        AUDIOCLIENT_ACTIVATION_PARAMS params{};
        params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
        params.ProcessLoopbackParams.TargetProcessId = pid;
        params.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
        PROPVARIANT prop{};
        prop.vt = VT_BLOB;
        prop.blob.cbSize = sizeof(params);
        prop.blob.pBlobData = reinterpret_cast<BYTE*>(&params);
        ComPtr<IActivateAudioInterfaceAsyncOperation> op;
        check(ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK, __uuidof(IAudioClient),
                                          &prop, activation.Get(), &op));
        if (WaitForSingleObject(activation->done, 10000) != WAIT_OBJECT_0)
            throw std::runtime_error("Audio activation timeout");
        check(activation->result);
        WAVEFORMATEX fmt{};
        fmt.wFormatTag = WAVE_FORMAT_PCM; fmt.nChannels = 2; fmt.nSamplesPerSec = 44100;
        fmt.wBitsPerSample = 16; fmt.nBlockAlign = 4; fmt.nAvgBytesPerSec = 176400;
        check(activation->client->Initialize(AUDCLNT_SHAREMODE_SHARED,
            AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM,
            0, 0, &fmt, nullptr));
        HANDLE ready = CreateEventW(nullptr, FALSE, FALSE, nullptr);
        check(activation->client->SetEventHandle(ready));
        ComPtr<IAudioCaptureClient> capture;
        check(activation->client->GetService(IID_PPV_ARGS(&capture)));
        std::mutex mutex;
        std::condition_variable changed;
        std::deque<Packet> queue;
        size_t queuedBytes = 0;
        unsigned long long dropped = 0;
        std::atomic_bool failed = false;
        // Pipe I/O never runs in the WASAPI producer. Queue is bounded to 800 ms.
        std::jthread writer([&](std::stop_token stop) {
            while (!stop.stop_requested()) {
                Packet packet;
                {
                    std::unique_lock lock(mutex);
                    changed.wait_for(lock, std::chrono::milliseconds(40), [&] { return !queue.empty() || stop.stop_requested(); });
                    if (queue.empty()) continue;
                    packet=std::move(queue.front()); queue.pop_front(); queuedBytes-=packet.bytes.size();
                    packet.header.dropped|=dropped;
                }
                if (fwrite(&packet.header,1,sizeof(Header),stdout)!=sizeof(Header) ||
                    fwrite(packet.bytes.data(),1,packet.bytes.size(),stdout)!=packet.bytes.size() || fflush(stdout)!=0) {
                    failed = true; break;
                }
            }
        });
        check(activation->client->Start());
        fprintf(stderr, "Process-tree capture PID %lu; isolation acceptance UNVERIFIED\n", pid);
        HRESULT captureResult = S_OK;
        uint64_t sequence=0;
        while (!failed && WaitForSingleObject(process, 0) == WAIT_TIMEOUT) {
            if (WaitForSingleObject(ready, 250) != WAIT_OBJECT_0) continue;
            UINT32 frames = 0;
            captureResult = capture->GetNextPacketSize(&frames);
            while (SUCCEEDED(captureResult) && frames) {
                BYTE* data = nullptr; DWORD flags = 0;
                UINT64 sampleIndex=0,qpc100ns=0;
                captureResult = capture->GetBuffer(&data, &frames, &flags, &sampleIndex, &qpc100ns);
                if (FAILED(captureResult)) break;
                std::vector<BYTE> bytes(frames * fmt.nBlockAlign, 0);
                Packet packet;
                packet.header.size=static_cast<uint32_t>(bytes.size());
                if ((flags & AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY) && sequence>0) ++sequence;
                packet.header.sequence=sequence++; packet.header.index=sampleIndex;
                packet.header.endNs=qpc100ns*100+static_cast<uint64_t>(frames)*1000000000/44100;
                if ((flags & AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR) || qpc100ns==0) {
                    packet.header.dropped|=(uint64_t{1}<<63);
                    LARGE_INTEGER counter,frequency; QueryPerformanceCounter(&counter); QueryPerformanceFrequency(&frequency);
                    packet.header.endNs=static_cast<uint64_t>(static_cast<long double>(counter.QuadPart)*1000000000/frequency.QuadPart);
                }
                if (!(flags & AUDCLNT_BUFFERFLAGS_SILENT)) memcpy(bytes.data(), data, bytes.size());
                capture->ReleaseBuffer(frames);
                {
                    std::lock_guard lock(mutex);
                    while (!queue.empty() && queuedBytes + bytes.size() > 141120) {
                        queuedBytes -= queue.front().bytes.size(); queue.pop_front(); ++dropped;
                    }
                    if (bytes.size() <= 141120) { queuedBytes += bytes.size(); packet.bytes=std::move(bytes); queue.push_back(std::move(packet)); }
                    else ++dropped;
                }
                changed.notify_one();
                captureResult = capture->GetNextPacketSize(&frames);
            }
            if (FAILED(captureResult)) break;
        }
        activation->client->Stop();
        writer.request_stop(); changed.notify_all();
        writer.join();
        CloseHandle(ready); CloseHandle(process);
        fprintf(stderr, "Source ended; dropped native packets: %llu\n", dropped);
        return 2; // Supervisor re-enumerates Discord. Never falls back to system audio.
    } catch (const std::exception& e) {
        fprintf(stderr, "Process capture unavailable: %s\n", e.what()); return 1;
    }
}
