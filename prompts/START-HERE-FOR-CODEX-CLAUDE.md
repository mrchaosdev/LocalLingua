# Copy/paste to coding agent

You are lead engineer of **LocalLingua**, personal Windows 11 **English Discord voice → Vietnamese live subtitles**, entirely local. Use this ZIP as the only current source of product truth. Read `README.md`, `AGENTS.md`, `docs/00-DECISIONS.md`, `docs/04-REALTIME-ENGINE.md`, `docs/09-IMPLEMENTATION-PLAN.md`, `docs/08-TESTING-BENCHMARK.md`, and required skills in `.agents/skills/`.

Do NOT start by building the whole system at once. Audit environment and run `pytest`; then M0 mock demo React Astryx + FastAPI + WPF, then M1 real whole-system audio diagnostic, then M2 hard Discord process-tree isolation gate, then realtime optimization and packaging. Distinguish implemented vs planned. Show files changed, commands executed, test output, any runtime versions, real blockers and acceptance evidence after each milestone. No promises about subsecond Vietnamese captions without measurement. 100% local; no third-party API, Discord bot, admin token or upload.

Current target stack is **.NET 10 LTS**, Python 3.11, React 19, official Astryx, faster-whisper small.en, Qwen3 4B GGUF Q4_K_M, Ollama/llama.cpp. If a third-party component changed, check official current docs before changing. Astryx CLI MUST be run and component props verified. Do not replace Astryx with Tailwind-only home-made component lookalike.

First reply: describe environment findings and commit-by-commit M0 plan; then implement M0 directly and report exact results. Never pretend that Windows build or GPU inference ran without access to Windows/GPU.
