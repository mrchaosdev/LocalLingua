// LocalLingua process-tree loopback. API reference: Microsoft ApplicationLoopback sample.
// Raw 44100 Hz stereo PCM16 stdout; diagnostic text stderr. No audio files.
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
using namespace Microsoft::WRL;
void check(HRESULT hr) { if (FAILED(hr)) throw std::runtime_error("Windows audio API failed"); }

DWORD discordRoot() {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot enumerate processes");
    std::map<DWORD, DWORD> parents;
    PROCESSENTRY32W p{}; p.dwSize = sizeof(p);
    if (Process32FirstW(snap, &p)) do {
        if (_wcsicmp(p.szExeFile, L"Discord.exe") == 0) parents[p.th32ProcessID] = p.th32ParentProcessID;
    } while (Process32NextW(snap, &p));
    CloseHandle(snap);
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

int main() {
    _setmode(_fileno(stdout), _O_BINARY);
    try {
        check(CoInitializeEx(nullptr, COINIT_MULTITHREADED));
        DWORD pid = discordRoot();
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
        std::deque<std::vector<BYTE>> queue;
        size_t queuedBytes = 0;
        unsigned long long dropped = 0;
        std::atomic_bool failed = false;
        // Pipe I/O never runs in the WASAPI producer. Queue is bounded to 800 ms.
        std::jthread writer([&](std::stop_token stop) {
            while (!stop.stop_requested()) {
                std::vector<BYTE> bytes;
                {
                    std::unique_lock lock(mutex);
                    changed.wait_for(lock, std::chrono::milliseconds(40), [&] { return !queue.empty() || stop.stop_requested(); });
                    if (queue.empty()) continue;
                    bytes = std::move(queue.front()); queue.pop_front(); queuedBytes -= bytes.size();
                }
                if (fwrite(bytes.data(), 1, bytes.size(), stdout) != bytes.size() || fflush(stdout) != 0) {
                    failed = true; break;
                }
            }
        });
        check(activation->client->Start());
        fprintf(stderr, "Process-tree capture PID %lu; isolation acceptance UNVERIFIED\n", pid);
        HRESULT captureResult = S_OK;
        while (!failed && WaitForSingleObject(process, 0) == WAIT_TIMEOUT) {
            if (WaitForSingleObject(ready, 250) != WAIT_OBJECT_0) continue;
            UINT32 frames = 0;
            captureResult = capture->GetNextPacketSize(&frames);
            while (SUCCEEDED(captureResult) && frames) {
                BYTE* data = nullptr; DWORD flags = 0;
                captureResult = capture->GetBuffer(&data, &frames, &flags, nullptr, nullptr);
                if (FAILED(captureResult)) break;
                std::vector<BYTE> bytes(frames * fmt.nBlockAlign, 0);
                if (!(flags & AUDCLNT_BUFFERFLAGS_SILENT)) memcpy(bytes.data(), data, bytes.size());
                capture->ReleaseBuffer(frames);
                {
                    std::lock_guard lock(mutex);
                    while (!queue.empty() && queuedBytes + bytes.size() > 141120) {
                        queuedBytes -= queue.front().size(); queue.pop_front(); ++dropped;
                    }
                    if (bytes.size() <= 141120) { queuedBytes += bytes.size(); queue.push_back(std::move(bytes)); }
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
