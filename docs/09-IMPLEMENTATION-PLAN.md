# Milestones, estimates and agent execution plan

> Sequence is dependency-based. No vague promise that a 12GB GPU will meet p95 until measured. Use each gate in `08-TESTING-BENCHMARK.md`.

## M0 — Repo / contracts / UI / fake events (first)
**Deliver:** Python FastAPI server on localhost, WebSocket event fan-out, status, demo translated captions, React Astryx dashboard, WPF overlay shell, protocol schema and tests. **Done when:** one terminal sends fake events; both clients render correctly, no AI download needed. **Suggested effort:** 0.5–1 day for experienced dev, not a delivery guarantee.

## M1 — Windows system loopback & first offline AI
**Deliver:** NAudio WASAPI whole-device capture on Windows (clearly diagnostics), ingest with PCM format handshake, ring buffer, basic VAD, faster-whisper small.en, Qwen translation via Ollama. **Done when:** captured YouTube/Discord audio appears in EN and VI after real inference; model run documented; no audio writes. **Effort unknown until CUDA/CTranslate2 drivers verified**.

## M2 — Capture Discord only (release blocker)
**Deliver:** integrate Windows `AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK` using Microsoft official sample as reference; process-tree selection, device and process recovery, separate output signal tests. **Done when:** YouTube excluded, Discord included, restart works. Don't mislabel NAudio endpoint capture as app-isolated.

## M3 — Realtime correctness/performance
**Deliver:** real VAD, stable prefix, partial/final translation, bounded queues, stale translation cancellation/result revision protection, history and state diagnostics, latency traces, 30-minute test. **Done when:** 30-minute regression passes and P50/P95 reported as measured values.

## M4 — Polished Astryx + overlay UX
**Deliver:** density/palette, sound level meter, multi-monitor overlay, caption controls, hotkeys, glossary and explicit export. **Done when:** owner can operate from mouse/keyboard without terminals.

## M5 — Personal release packaging
**Deliver:** startup/service supervision, local security token/origin protection, offline assets, documented model licensing, portable installer/build, software update plan, crash recovery. **Done when:** clean Windows 11 install can run offline after models downloaded.

## M6 optional — model upgrade experiment
Compare Nemotron streaming ASR versus faster-whisper, TranslateGemma versus Qwen on fixed corpus. Only promote if meaningful quality/latency gain without fragility.

## First 10 agent tasks
1. Environment audit, check packages, nvidia-smi, .NET 10, Python 3.11.
2. Run `pytest` and explain coverage.
3. Build React web frontend with Astryx CLI docs; demo WS works.
4. Build WPF overlay on actual Windows; make it topmost, draggable.
5. Prove system audio endpoint capture with isolated loopback diagnostic.
6. Normalize PCM/resampling and test 16kHz data.
7. Verify faster-whisper CUDA compatibility and 30s English fixture.
8. Verify Ollama Qwen 4B translation and format/safety tests.
9. Prove Discord-only process capture via Microsoft sample, then integrate.
10. Optimize partial/final segmentation, latency and 30-min soak.

## Agent handoff format
Each task result must contain: current branch/files; commands run; tests (exact output); what is simulated vs real; model/revision; current blockers; next task. No green checkmarks without reproduction.
