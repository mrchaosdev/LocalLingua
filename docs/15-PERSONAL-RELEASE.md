# Personal development bundle — Windows 11 x64

Status: implementation candidate. No clean-PC/offline installation has been tested. M2 isolation and M3 performance remain release blockers.

## Prepare a build machine

Install .NET 10 SDK, Python 3.11, Node >=22.13, VS C++ build tools, CMake and recent Windows SDK. Install engine dependencies in a clean build environment. Run deferred automated tests before treating a bundle as a release. The packaging script builds assets; it does not claim the acceptance gates pass.

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package-personal.ps1
```

The script creates a NEW timestamped directory under release/, publishes self-contained .NET win-x64 programs, compiles the process helper, freezes the Python engine with PyInstaller and copies offline web assets. It generates BUILD-STATUS.json (unverified) and file checksums. It never replaces an existing release. GPU libraries may require compatible NVIDIA CUDA/cuDNN installation on the target PC. Binary freezing and native loading are unverified.

## Configure the target PC

1. Download models once from official sources (docs/02). Record immutable repository revisions, GGUF filename, Ollama digest and licenses in your private model inventory. Do not use mutable tags as release evidence.
2. Install/start local Ollama. No model weights or Ollama runtime are bundled. Ensure its model is available before disconnecting the internet.
3. In the bundle's engine/.env use mock/demo first, then copy engine/.env.gpu.example over .env. Set WHISPER_MODEL and VAD_MODEL_PATH to ABSOLUTE local paths. Keep OFFLINE_MODE=1 and OLLAMA_URL=http://127.0.0.1:11434.
4. Double-click LocalLingua.Launcher.exe. A tray icon starts the engine and native audio host, opens overlay and dashboard. Launching does not start transcription; click Bắt đầu explicitly.
5. Tray menu opens dashboard/overlay or exits all owned components. A bounded restart policy reports startup failure. Engine shutdown requests model unload; after a grace period, remaining owned processes are terminated. Never terminate unrelated Ollama/Discord processes.
6. The default capture is Discord process tree; absence/failure of Discord retries visibly and never switches to whole-system capture. Use system diagnostic only by running AudioHost with --system-diagnostic manually.

## Acceptance before use

Run M0–M5 gates on Windows 11, including YouTube exclusion, Discord restart/device changes, 30-minute speech/silence tests, keyboard/DPI/monitor review, no external runtime requests and no files containing audio/transcripts. End-to-end latency requires synchronized audio/capture/render instrumentation, which is still pending. No P50/P95 target is claimed.

## Updates / recovery

There is no automatic updater or background download. Quit the tray app, keep model files separately, extract a NEW version folder, copy reviewed non-secret configuration, re-run acceptance, then launch. Keep the previous folder for rollback. The runtime generates a temporary token per launcher session; no account credential or Discord token is needed.

## Residual limitations

Unsigned binaries may show Windows warnings. There is no MSIX/installer/signing pipeline. Exact model revision lock, full dependency license notices, clean-machine validation, capture clock synchronization and persistent technical crash diagnostics remain pending. A private development bundle is not a validated redistributable release.
