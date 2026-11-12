# ADR / Architecture decisions

| ID | Status | Decision | Why / trade-off |
|---|---|---|---|
| ADR-001 | Accepted | Windows 11, one user, English → Vietnamese ONLY | Limits latency, cost, surface area |
| ADR-002 | Accepted | Local by default: no cloud inference/telemetry | Personal privacy |
| ADR-003 | Accepted | Native .NET **10 LTS** audio integration and WPF overlay | Windows audio capture + transparent topmost window |
| ADR-004 | Accepted | React 19 + official **Astryx** for dashboard | Agent-ready component library, theming; not an imitation |
| ADR-005 | Accepted | Python 3.11 + FastAPI + WebSocket engine | Speech/translation ecosystem |
| ADR-006 | Accepted | System loopback *diagnostic* first, Discord process-tree loopback *required before v1* | Different capability; avoid false claim |
| ADR-007 | Accepted | Faster-whisper small.en baseline; Nemotron as benchmark challenger | Reliable baseline before streaming optimization |
| ADR-008 | Accepted | Qwen3 4B GGUF quantized local translation baseline, TranslateGemma challenger | Fast practical Windows path; benchmark choice |
| ADR-009 | Accepted | Two-tier captions: tentative revisions + immutable finalized utterance | Balances latency and stability |
| ADR-010 | Accepted | In-memory by default; export with explicit action | Do not build database before realtime proof |
| ADR-011 | Accepted | Streaming UI over localhost; web itself does NOT listen to desktop Discord | Browser permission model limitation |
| ADR-012 | Accepted | Latency-first test gate, 30-minute steady-state test | Backlogs doom live translation |
| ADR-013 | Accepted | No embeddings/RAG/vector DB/agent orchestration in v1 | Unnecessary complexity |
| ADR-014 | Accepted | No user identification from mixed Discord audio | Speaker diarization not reliable by default |

## Not decided: require measurement
- Which GPU model/driver? User only confirmed 12 GB VRAM. Verify.
- Is direct Windows Nemotron streaming practical? Benchmark after baseline works.
- Is translation via Qwen faster or more meaningful than TranslateGemma for Discord/Web3 language? Collect test corpus.
- Does actual process capture work across Discord updates, GPU devices and restarts? Test process tree/detachment.
- Can p95 partial translation be ≤2s while preserving meaning? Treat as target, not a promise.

## Release phases
- v0: demo UI/backend/mock no capture.
- v0.1: native system output capture + real ASR/translator (diagnostic).
- v0.2: Discord-isolated capture proven + reconnect.
- v0.3: stability, metrics, 30-min test + overlay.
- v1.0: packaged local personal app, privacy and error handling polished.
