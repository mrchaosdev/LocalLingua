# Troubleshooting decision tree

**Dashboard blank** → check 5173 browser console / 8765 `/health`, `npm install`, Astryx CSS import order, `npx @astryxdesign/cli init` and component API docs.

**WebSocket disconnected** → ensure Uvicorn bound `127.0.0.1`, firewall/port correct, `/ws/events` reachable, inspect browser DevTools WS upgrade. Disconnected UI should show offline.

**Whole-system audio instead of Discord-only** → expected in diagnostic starter (`WasapiLoopbackCapture`). Implement process loopback according to M2. Do not workaround using `Discord token` or unofficial bot.

**No audio captured** → check output render endpoint, device channel routing, whether Discord is actually playing sound, binary format handshake. Trigger video speaker test locally with permission.

**Slow translations** → inspect per-stage timers and Ollama GPU acceleration, queue depth; try shorter utterances, smaller quantization, `max_output_tokens`; do not flood model with one request per word.

**Whisper CUDA DLL error** → check CUDA 12, cuBLAS and cuDNN 9 for current CTranslate2, check Python env; fallback CPU temporarily and label degraded. No arbitrary CUDA downgrade.

**English gibberish on silence** → apply VAD/silence gating and language=en, avoid transcribing 0-RMS buffers, verify audio scaling / resample quality.

**Repeated subtitles** → compare utterance IDs, revisions, rolling-window overlap; implement LCS dedupe and don't treat each rolling prediction as final.

**VRAM OOM** → reduce Qwen context, ASR footprint, avoid simultaneous model replicas, check other GPU apps; bench one model at a time to isolate.

**Overlay invisible/click blocked** → check topmost state, DPI, window bounds, mouse passthrough lock. Expose hotkey to unlock overlay; test multi-monitor.

**Ollama model not found** → check `ollama list`; `OLLAMA_MODEL` must match registered identifier. Hugging Face model page by itself isn't automatically installed.
