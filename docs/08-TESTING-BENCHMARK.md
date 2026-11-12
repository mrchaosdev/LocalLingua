# Test, benchmark and quality gates

## Test levels
- **Unit**: stable prefix, revisions, transcriber normalization, translator payload cleanup, audio frame parsing, silence gate, bounded queues, error handling.
- **Integration**: stream 30s PCM English to backend → correct partial/final ordering, translated text and UI display. Use deterministic prerecorded WAV with known timestamps.
- **End-to-end**: real Discord native app → real process capture → real GPU models → WPF overlay + Astryx dashboard.
- **Soak**: 30 min continuous conversation, 30 min silence, 10 reconnects, background/foreground app.

## Audio test corpus
Collect **with permission** 20–30 minutes across: slow/fast American/British accents, background music, overlapping voices, interruptions, acronyms (NFT, DAO, mint, whitelist, token, alpha, seed, mainnet, airdrop, snapshot), crypto numbers, dates, negation, mixed chat. Annotate a short held-out reference EN+VI; do not upload confidential recordings.

## Metrics
| Metric | Definition | Example method |
|---|---|---|
| Word Error Rate | EN ASR edit-distance over human reference words | `jiwer` over annotated segments |
| Meaning adequacy | Human-rated Vietnamese preserving sense | 1–5 scale, blind pairwise Qwen/TranslateGemma |
| Negation/number accuracy | Critical correct/incorrect cases | Tagged golden corpus |
| First EN partial | Relevant audio onset to visible EN | Audio/video capture sync |
| First VI partial | Relevant audio onset to readable translated clause | Annotated test harness |
| VI final age | utterance end to final VI screen | Timestamped injection/visual instrumentation |
| Translation service time | request submission to model completion | `time.perf_counter()` |
| Queue audio age | Last played audio sample to ASR processing input | Source sample ID + calibrated clock |
| UI event delay | server event → render ack | Local timestamps + trace ID |
| VRAM RSS CPU | per-process steady state and peak | `nvidia-smi`, process telemetry |
| Drop/reconnect | loss count, restart recovery | Kill/restart capture and Discord |

## Performance goals (UNVERIFIED)
- P50 VI partial ≤2s; P95 VI final ≤5s after utterance end.
- 30-minute lag trend ≤0.5s increase from first five minutes to last five minutes.
- 0 silent loss of already-finalized captions. No repeated 3+ word overlapping line in final transcript.
- No VRAM OOM on GPU 12GB while Discord and browser open.
- No non-Discord audio included when Discord isolation selected.

## Gate M0 (mock demo)
- Python `pytest` green and app `/health` returns 200.
- UI connects to WS, 'Demo' emits EN+VI without models and shows status.
- `.NET` projects at `net10.0-windows`; GUI renders with Windows DPI settings.

## Gate M1 (system audio diagnostic)
- Captures device output reliably 10 min; no playback distortion.
- WAV fixture test ASR transcribes English; Qwen local returns Vietnamese.
- Full system source conspicuously marked, not shipped as final Discord-only feature.

## Gate M2 (Discord isolation) — hard blocker
- When ONLY YouTube produces sound, captured RMS stays near zero.
- When ONLY Discord speaks, captured RMS increases and speech transcribed.
- When BOTH play, output excludes YouTube (subjective and instrumental listening test).
- Restart Discord and switch audio output, recover within an observed bounded interval; no claims until measured.

## Gate M3 (realtime)
- 30 min active English, measured P50/P95; no steadily growing delay.
- Partial output updates without contradictory duplicated finals; translation queue bounded under overload.
- Visual dashboard shows partial/final distinction and health state.

## Gate M4 (personal release)
- Offline after download, standalone startup scripts/install, crash handling, zero default audio retention, local auth/origin security, exit/unload GPU.
- A user can open Discord and start overlay without developer terminal.

## Automated starter tests
`cd services/engine && python -m pytest -q`. Tests in ZIP are meaningful protocol/core tests, **not** evidence of latency and real capture. An actual benchmark report MUST record GPU model, OS build, SDK, driver, model revisions, profile, duration, raw anonymized times, summary table and screenshots.
