# LocalLingua — Windows 11 English → Vietnamese subtitles

Local-first personal desktop app: official Astryx React dashboard, WPF overlay, Discord process-tree capture, faster-whisper small.en and local Ollama Qwen3 4B Q4_K_M.

**M0–M5 source implementation is present. Runtime acceptance is unverified.** The owner explicitly requested finishing code without running tests. This repository does not contain a tested installer or bundled model weights. See [implementation coverage and usage](docs/16-COMPLETE-IMPLEMENTATION.md), [evidence ledger](BUILD_VERIFICATION.md) and [milestone report](reports/IMPLEMENTATION-2026-11-12.md).

Target remains .NET **10**, Python **3.11**, Windows 11 x64, NVIDIA **12 GB VRAM**. VRAM fit and realtime latency must be measured on the target PC. No cloud inference, Discord bot or account token.

## Features

- Discord process-tree capture, explicit whole-system diagnostic mode, process/device selection and recovery.
- Start/Pause/Stop controls stop audio acquisition; finalized translations drain in bounded workers.
- Local ASR/translation, Silero ONNX VAD, stable partial/final revisions, profiles and visible overload/error states.
- Official Astryx controls, matched EN/VI captions, RAM history/search, glossary, dark/light mode, TXT/MD/SRT exports.
- Topmost draggable/resizable overlay, monitor switching, font/opacity/English preferences, click-through and global unlock hotkey.
- Source clock / render timing instrumentation and explicit metadata-only trace export.
- Official model downloader with immutable revision/hash/license inventory, local readiness and GPU diagnostics.
- Per-run auth/Origin checks, tray supervision, technical crash metadata, portable ZIP and optional Windows installer recipe.

## Build / launch

On a build PC install .NET 10 SDK, Python 3.11, Node >=22.13, VS C++ build tools, recent Windows SDK, CMake; install Inno Setup 6 for installer output.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package-personal.ps1
# Or also build the per-user installer:
powershell -ExecutionPolicy Bypass -File scripts/package-personal.ps1 -Installer
```

The script builds assets/executables and collects notices; it does not execute pytest or runtime acceptance tests. Launch the output's **LocalLingua.Launcher.exe**. It opens dashboard/overlay and starts AudioHost in standby. In **Nguồn và model**, configure local AI or use the explicitly labelled mock/demo first. Install Ollama separately, then click the official model download action once. See [full workflow](docs/16-COMPLETE-IMPLEMENTATION.md).

Models are not downloaded when the app starts. Clicking the installer action downloads official model files, records immutable revisions/SHA256 and applies local GPU paths on the next launch. Runtime remains offline after dependencies/models are installed.

For development, run scripts/setup-engine.ps1 -Gpu, npm.cmd ci in apps/web, then scripts/run-engine.ps1 with a common LOCALLINGUA_TOKEN shared by AudioHost and overlay. The script prints a local dashboard link containing the temporary fragment token. Vite dev uses scripts/run-web.ps1 and http://127.0.0.1:5173/#token=... . Source settings and first-run downloader use the same dashboard APIs.

## Privacy / limits

Audio and transcripts stay in memory unless you explicitly export text. The rolling server history holds 70 EN/VI events and exposes eviction counts. Preferences, geometry and rotating technical metadata are saved locally; technical log messages exclude transcript/audio bodies. Tokens expire with the launcher and are scoped to local clients.

Discord isolation, target-PC GPU compatibility, visual/DPI behavior, timing accuracy and clean offline installation have not been accepted. System capture is clearly diagnostic and is never a silent fallback. Metrics show actual collected samples or no value; no performance target is presented as achieved.

## Project instructions and deferred checks

Read [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md), [starting prompt](prompts/START-HERE-FOR-CODEX-CLAUDE.md), docs/00, docs/04 and docs/09. Original kit/spec remain in Git history and FULL_SPEC.md. [Audio v2 contract](contracts/audio-frame-v2.md) describes framing/clock scope. [M2 acceptance sheet](reports/M2-ISOLATION-ACCEPTANCE.md) lists isolation cases for later.

Deferred commands (not run for this delivery): services/engine/.venv/Scripts/python.exe -m pytest -q; Windows/native builds; GUI/inference and 30-minute benchmarks in docs/08. GitHub Actions are manual-only and will not run on push.
