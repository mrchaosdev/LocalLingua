> CURRENT IMPLEMENTATION: the original kit text below is preserved as design/history. Source completion is described in docs/16-COMPLETE-IMPLEMENTATION.md and contracts/audio-frame-v2.md. Runtime acceptance remains unverified by user request.

# Windows 11 operator/developer runbook

## Prerequisites
- Windows 11 x64, NVIDIA driver with CUDA compatibility, 12GB VRAM GPU, 32GB RAM.
- .NET 10 SDK: https://dotnet.microsoft.com/en-us/download/dotnet/10.0
- Python 3.11 from python.org, Node 22 or newer compatible LTS, npm, Git.
- Ollama Windows or llama.cpp; install only after mock pipeline works.
- Visual Studio 2026 recommended for native WPF/C++ Windows SDK; developer mode optional.

## Commands
```powershell
# verify versions
winver
dotnet --info
py -3.11 --version
node --version
npm --version
nvidia-smi

# API backend
cd services/engine
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765

# smoke test /health
Invoke-RestMethod http://127.0.0.1:8765/health

# web frontend, another terminal
cd apps/web
npm install
npx @astryxdesign/cli init
npm run dev

# native host, another terminal
cd apps/windows/LocalLingua.AudioHost
dotnet restore
dotnet run

# overlay, another terminal
cd apps/windows/LocalLingua.Overlay
dotnet restore
dotnet run
```

## Real AI provider activation
Edit `services/engine/.env`:
```env
ASR_BACKEND=whisper
WHISPER_MODEL=small.en
WHISPER_DEVICE=cuda
WHISPER_COMPUTE=int8_float16
TRANSLATE_BACKEND=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```
Model ID must match `ollama list` exactly; changing model may need restart. To isolate problems set `ASR_BACKEND=mock` or `TRANSLATE_BACKEND=mock` separately.

## Runtime check
- Confirm `/api/status` reports capture connected and backend choices. Use `/api/control` `mode=start|pause|stop`; demo is `/api/demo`.
- Test original stream with a permitted prerecorded speech sample before live Discord.
- If no sound check Windows output device/headphones and host console.
- If backend fails to start, check port 8765, package dependencies, .env and Python 3.11.
- If model OOM check `nvidia-smi`, close GPU-heavy applications, reduce model/context; do not silently send audio to cloud.

## Export & retention
In-memory events only in scaffold (bounded deque). No file output from backend. A later Export button should create TXT/MD/SRT only upon click after user chooses file and sees consent reminder. Don't write private audio into Git repo.

## Updating code
Pin dependency versions and verify Astryx package compatibility; run `npm run build`, `pytest`, `dotnet build` on Windows. Store build logs for reproducibility; no auto-updater in v1.
