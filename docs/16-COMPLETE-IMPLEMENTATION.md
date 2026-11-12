# LocalLingua — implementation coverage (2026-11-12)

This document describes source implementation for the v1 scope in docs/01 and milestones M0–M5. Tests are explicitly disabled for this delivery by the owner. No acceptance or performance claim follows from code coverage.

| Requirement | Implementation |
|---|---|
| F01 system output | AudioHost NAudio capture; explicit diagnostic source; output endpoint selection |
| F02 Discord isolation | Native Windows process-tree activation; unique root discovery / selected PID; no system fallback |
| F03 ASR partial/final | Serialized faster-whisper, English-only, stable-prefix revisions, voiced minimum, forced bounded segmentation |
| F04 EN→VI | Local Ollama Qwen, glossary/context, thinking cleanup, no cloud endpoint |
| F05 bounded realtime | 800ms PCM bound; ASR/translation workers; bounded final FIFOs; latest partial replacement/cancellation; visible gaps/overflow |
| F06 captions window | WPF topmost, drag/resize, font/opacity/English controls, monitor cycling, remembered geometry, click-through/unlock hotkey |
| F07 dashboard | Official Astryx components; current matched EN/VI, RAM history/search, source/PID/endpoint, profiles, diagnostics |
| F08 offline runtime | Local model paths, implicit downloads disabled, no CDN, bundled assets; model installer is explicit one-time network action |
| F09 Start/Pause/Stop | Host standby with control polling; only Start opens capture; Pause/Stop cancel native/WASAPI and finalize already-captured work |
| F10 privacy | Visible capture state; no audio/transcript files by default; rotating technical metadata without log-message bodies |
| F11 glossary | Add/list/delete in RAM; bounded hints, no instructions/tools executed |
| F12 export | Explicit TXT/MD/SRT; file chooser where browser supports it; timed SRT rejects untimed demo history |
| F13 profiles | Fast/Balanced/Quality schedule, beam and token limits; CPU/CUDA/compute choice; no unmeasured profile recommendation |
| F14 recovery | Engine/host/Ollama ownership supervision, bounded restart, process PID rebind, device changes, failed worker recreation |

F15 speaker identity and M6 model comparison remain outside the v1 scope. No speaker identity is inferred.

## User workflow

1. Build a portable bundle with scripts/package-personal.ps1, or pass -Installer for an Inno Setup 6 installer. Build machine needs .NET 10, Python 3.11, Node, VS C++ tools/CMake/Windows SDK. No framework downgrade.
2. Install Ollama from its official Windows installer (tray menu opens the official page). The launcher can start an installed local Ollama server when needed; it only terminates a server that it started.
3. Open LocalLingua.Launcher.exe. Source begins idle. Open **Nguồn và model**.
4. First installation: click **Tải và cài model chính thức**. Downloader resolves official repository revisions to immutable SHAs, verifies available LFS hashes, writes SHA256/license inventory and imports GGUF locally. Needs at least 8 GiB free disk; no weights are bundled into the app installer. After completion, quit/reopen the tray app to apply the saved GPU paths/profile.
5. Review local paths, GPU compute, source and endpoint/PID. Save while stopped; optional **Nạp model local** catches missing dependencies before speech. Start also loads Whisper before opening capture.
6. Click **Bắt đầu**; Stop/Pause stop acquisition and let committed speech finish translation. Restarting a lost Discord source never switches to system audio. Stable Discord.exe is supported; Canary/PTB naming is not selected.
7. Read subtitles in dashboard and/or overlay. Overlay Ctrl+Alt+L toggles click-through; lock is refused if the unlock hotkey cannot register. Ctrl+Alt+O hides/shows; +/- changes font; Ctrl+Up/Down changes opacity; Màn hình cycles monitors. It starts unlocked.
8. Export only when desired. Server retains a bounded rolling window of 70 EN/VI events; eviction count is visible. Text exports contain that retained window, not the whole meeting. Stopping/closing the engine releases inference resources.

## Timing and diagnostics

See contracts/audio-frame-v2.md. Source QPC and UI clocks are calibrated. Captions carry source interval and traces. Browser/WPF render acknowledgements populate bounded estimated timing distributions; first-VI-partial and final-render timing are separate. JSON export includes hardware/model/profile information. A first/last five-minute lag comparison is available only after 30 minutes with final-render samples in both windows.

Trace export contains metadata, no English/Vietnamese or audio. It does include technical model paths/profile when explicitly exported. Geometry/preferences and bounded technical crash records live under LocalAppData/LocalLingua; transcripts do not.

## Packaging / recovery

The build recipe collects installed Python/JS/NuGet notices and exact package inventories, creates file hashes, a portable ZIP and optionally a per-user unsigned installer. It bundles Python and .NET runtimes; the target still needs a compatible NVIDIA driver/CUDA/cuDNN and a separately installed Ollama application. No account or Discord credential is required. Tokens are regenerated each launcher run and held in process memory / per-tab sessionStorage, without localStorage or query strings.

Updates are manual: exit tray, install/extract a new folder, retain model/config directory, reopen. Prior bundle can be retained for rollback. Installer uninstallation leaves user model/config files intact. No updater downloads or code execution from captions.

## Verification boundary

Only source/TypeScript syntax/compilation checks were performed in this delivery. No pytest, native build, GUI launch, capture, inference, benchmark, model download, installer build or clean-PC run. Those acceptance tasks remain unverified by explicit user instruction; the application does not assert verified=true or display invented latency/VRAM results.

Reference APIs for the completed source:
- Ollama local-only mode and preload: https://docs.ollama.com/faq
- Ollama show response remote_host/remote_model and local model metadata: https://github.com/ollama/ollama/blob/main/api/types.go
- Qwen official GGUF artifact: https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/main
- Whisper converted checkpoint: https://huggingface.co/Systran/faster-whisper-small.en/tree/main
- Streaming resampler delay semantics: https://python-soxr.readthedocs.io/en/latest/soxr.html

The owned Ollama server is started with OLLAMA_NO_CLOUD=1. Before preloading/translating, the provider checks local GGUF metadata and rejects remote_host/remote_model or cloud tags; private speech is never deliberately sent to an Ollama cloud model.
