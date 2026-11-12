# LocalLingua — EN → VI local subtitles for Windows 11

Development implementation, **not an accepted realtime release**. This repository contains the original v2 build kit plus sequential M0–M5 implementation commits. The owner deferred tests on the development laptop. See [actual session evidence](reports/IMPLEMENTATION-2026-11-12.md) and [build verification](BUILD_VERIFICATION.md).

Target: Windows 11 x64, .NET **10**, Python **3.11**, NVIDIA **12 GB VRAM**. Official Astryx 0.7.12 / React 19 dashboard, WPF overlay, native process-loopback capture, faster-whisper small.en and local Ollama Qwen3 4B Q4_K_M. GPU fit and latency remain unmeasured.

| Milestone | Code added | Acceptance |
|---|---|---|
| M0 | bounded event snapshot/replay, immutable caption revisions, official Astryx | web compiles; runtime tests deferred |
| M1 | system diagnostic capture, streaming resampler, offline GPU profile | real audio/AI not run |
| M2 | native Windows Discord process-tree helper, root discovery/restart | native build and isolation NOT verified; release blocker |
| M3 | separate bounded workers, VAD, stabilization, generation guards, timing summaries | regression/30-minute soak NOT run |
| M4 | caption controls, glossary hints, explicit export, overlay controls/DPI | browser/native UX not reviewed |
| M5 | per-run auth, Origin/Host checks, tray supervisor, packaging script | portable bundle/clean offline installation NOT verified |

No audio or transcripts are written automatically. A transcript is downloaded only when you click export. Demo/mock captions are synthetic. Whole-system audio remains explicitly diagnostic; process capture never falls back to it automatically.

## Development

Read [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md), [starting prompt](prompts/START-HERE-FOR-CODEX-CLAUDE.md), then docs/00, docs/04 and docs/09. Task skills are under `.agents/skills/`.

From PowerShell in the project root:

```powershell
# Install dependencies separately; startup does not install from the internet.
powershell -ExecutionPolicy Bypass -File scripts/setup-engine.ps1
cd apps/web
npm.cmd ci
npm.cmd run build
cd ../..

# Set the SAME secret in the terminals used for engine, AudioHost and overlay.
# Prefer a random temporary value; do not commit it or put it in a URL query.
$env:LOCALLINGUA_TOKEN = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
powershell -ExecutionPolicy Bypass -File scripts/run-engine.ps1
# This displays a local dashboard link with a temporary fragment token.
```

In other terminals, set the same `LOCALLINGUA_TOKEN`, then run `scripts/run-overlay.ps1` or `scripts/run-audiohost.ps1 -SystemDiagnostic`. Without `-SystemDiagnostic`, AudioHost expects the native helper alongside its executable. Build it with `scripts/build-process-capture.ps1` (VS C++ tools + recent Windows SDK + CMake); copy the Release helper next to the built AudioHost.

For Vite development use `scripts/run-web.ps1` and open `http://127.0.0.1:5173/#token=<session-token>`. Packaged/production web assets are served by the engine at port 8765. Tokens remain in memory after the fragment is removed from the address bar.

The Start button gates audio processing and requires a connected host. It does not launch the capture executable. The packaged tray launcher manages executables.

## Local AI on the target GPU PC

Follow [model setup](docs/02-STACK-AND-MODELS.md). Run `scripts/setup-engine.ps1 -Gpu`, download the official Whisper checkpoint, Qwen GGUF and optional Silero ONNX model. Copy `services/engine/.env.gpu.example` to `.env` and set **absolute local model paths**. Install CUDA/cuDNN versions compatible with the installed CTranslate2. Offline mode rejects implicit Whisper downloads. Ollama must already be running locally with the exact configured model installed.

The default `.env.example` keeps both backends in mock mode. No cloud inference endpoint is supported. Model weights are excluded from Git and packaging. Record exact model revisions, Ollama digests, licenses and GPU driver before acceptance.

## Tests deferred — commands for the target PC

```powershell
cd services/engine
./.venv/Scripts/python.exe -m pytest -q
cd ../../apps/web
npm.cmd run build
npx.cmd @astryxdesign/cli doctor --built dist
```

Then build the .NET/native projects, perform [M2 isolation acceptance](reports/M2-ISOLATION-ACCEPTANCE.md), and run the tests/benchmarks in [docs/08](docs/08-TESTING-BENCHMARK.md). Syntax/build success does not pass native capture, model inference or latency gates.

For the tray launcher and development bundle, see [personal packaging](docs/15-PERSONAL-RELEASE.md). No installer executable or model is included in this repository.
