# LocalLingua — Windows 11 English → Vietnamese Live Subtitle Translator

**SPEC v2.0 | 12/11/2026 | Local-first, single-user, engineering handoff for Codex/Claude**

> This is a build kit containing product/technical/design documents, agent skills and an implementation scaffold. It is **not** a finished, benchmarked app, installer, or trained AI model. Individual model runtimes, the application-specific Discord capture backend and real-time performance must be verified on the target PC.

## Goal
While the owner listens to **English speech from Discord desktop on Windows 11**, display **Vietnamese subtitles** with as little delay as possible. Do not require a Discord bot, server administrator permissions, paid cloud API, or an internet connection after local installation/model download.

Personal target machine: Windows 11, **32 GB RAM, NVIDIA GPU with 12 GB VRAM** (exact GPU and driver to verify); no company infrastructure.

## User experience
1. Launch LocalLingua and the AI service. Open Discord, join a voice channel.
2. Select source `System loopback (diagnostic)` until process-specific capture passes acceptance; final selector `Discord process tree`.
3. Click Start. English tentative text and partial Vietnamese text appear, then settle into completed sentences.
4. Choose one or more views: **Astryx web dashboard** (`localhost:5173` during development), **standalone WPF overlay** (always-on-top), optional future desktop WebView2 wrapper.
5. Stop, inspect health/latency, optionally export text. Audio/transcript are NOT saved by default.

## Read in order
- [BUILD_VERIFICATION.md](BUILD_VERIFICATION.md) — honest list of tests performed vs unverified
- [docs/00-DECISIONS.md](docs/00-DECISIONS.md) — locked decisions and non-goals
- [docs/01-PRD.md](docs/01-PRD.md) — detailed product scope and UX
- [docs/02-STACK-AND-MODELS.md](docs/02-STACK-AND-MODELS.md) — all versions, Hugging Face URLs, download instructions
- [docs/03-ARCHITECTURE.md](docs/03-ARCHITECTURE.md) — components, event contract and dataflow
- [docs/04-REALTIME-ENGINE.md](docs/04-REALTIME-ENGINE.md) — scheduling, VAD, stability, translation, backpressure
- [docs/05-DESIGN-ASTRYX.md](docs/05-DESIGN-ASTRYX.md) — design language, component and accessibility rules
- [docs/06-WINDOWS-CAPTURE.md](docs/06-WINDOWS-CAPTURE.md) — real OS constraints, Discord isolation milestones
- [docs/07-SECURITY-PRIVACY.md](docs/07-SECURITY-PRIVACY.md)
- [docs/08-TESTING-BENCHMARK.md](docs/08-TESTING-BENCHMARK.md)
- [docs/09-IMPLEMENTATION-PLAN.md](docs/09-IMPLEMENTATION-PLAN.md)
- [docs/10-OPERATIONS.md](docs/10-OPERATIONS.md)
- [docs/11-CONTRACTS.md](docs/11-CONTRACTS.md)
- [docs/12-TROUBLESHOOTING.md](docs/12-TROUBLESHOOTING.md)
- [docs/13-REFERENCES.md](docs/13-REFERENCES.md)
- [docs/14-AGENT-TASKS.md](docs/14-AGENT-TASKS.md)

## Agent instructions
Read [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) first. Reusable procedural skills live under `.agents/skills/`; there are task prompts under `prompts/`. Every milestone is independently testable.

## Scaffold contents / honesty ledger
| Area | Included | Status |
|---|---|---|
| Python FastAPI service | HTTP health/status/control, UI WebSocket, ingest WebSocket, demo event emitter | **scaffold code** |
| ASR and translation | faster-whisper adapter, Ollama adapter, mock adapter | **code to test locally** |
| Audio | Windows system output loopback host, sends PCM | **diagnostic only**, not Discord-specific |
| WPF overlay | topmost, draggable, Vietnamese text + connection state | **starter** |
| Web UI | React 19 + Astryx neutral theme + live caption dashboard | **starter**; install dependencies |
| Discord-only process capture | Architecture, Microsoft sample link, acceptance gates | **not yet implemented** — must do M2 |
| Nemotron streaming ASR | Model link, research decision gate | **not integrated** |
| 30-min latency performance | Measurement plan and targets | **not measured** |

## Quick start: Windows PowerShell (development)
Install: .NET 10 SDK, Python 3.11, Node 22 LTS-compatible version, Git, NVIDIA driver; Ollama and model later.

```powershell
# 1) Python engine
cd services/engine
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765

# 2) React dashboard (new terminal)
cd apps/web
npm install
npm run dev
# Open http://127.0.0.1:5173 — click Demo (does not need AI)

# 3) Native system-loopback PoC (new terminal): captures ALL device output,
#    not just Discord; do not use in confidential meetings before isolation test.
cd apps/windows/LocalLingua.AudioHost
dotnet restore
dotnet run

# 4) WPF overlay (optional fourth terminal)
cd apps/windows/LocalLingua.Overlay
dotnet run
```

For *actual* ASR, run `pip install faster-whisper` in the backend venv and set `ASR_BACKEND=whisper` in `services/engine/.env` and install the CUDA/cuDNN requirements compatible with CTranslate2. For *actual* translation, install Ollama, pull a Qwen 4B local model and set `TRANSLATE_BACKEND=ollama`. **Both start in safe mock/demo mode.** Follow the detailed setup/diagnostics before entering a live meeting.

## Immutable product principles
- A graceful 2–5 second meaning-preserving translation is better than speculative 300ms hallucination.
- Partial captions may change; finalized captions must not be silently rewritten.
- If translation falls behind, drop stale **partial** jobs, never silently drop finalized speech.
- Local mode means no external inference calls, telemetry, CDNs or cloud transcript storage at runtime.
- No model, latency or VRAM claim without an actual measured run.
