> CURRENT IMPLEMENTATION: the original kit text below is preserved as design/history. Source completion is described in docs/16-COMPLETE-IMPLEMENTATION.md and contracts/audio-frame-v2.md. Runtime acceptance remains unverified by user request.

# Task board for autonomous coding agent

| Ticket | Priority | Work | Blocked by | Exit evidence |
|---|---|---|---|---|
| LL-001 | P0 | Run Python tests, verify environment | — | pytest and version log |
| LL-002 | P0 | Install Astryx / render browser demo | 001 | screenshot+build log |
| LL-003 | P0 | Validate WPF overlay WebSocket view | 001 | Windows screen recording+build log |
| LL-004 | P0 | Prove system audio loopback | 001 | allowed 30s file+RMS, no stutter |
| LL-005 | P0 | Validate PCM float32/s16 resampling | 004 | signal unit tests+SNR |
| LL-006 | P0 | Load Whisper small.en and measure | 005 | WER, VRAM, time report |
| LL-007 | P0 | Run Qwen3 GGUF via Ollama | 001 | original+VI 25 examples, time |
| LL-008 | P0 | Integrate working live pipeline | 006+007 | real speech → real VI |
| LL-009 | P0 | Official Discord process-loopback | 004 | exclude YouTube, include Discord |
| LL-010 | P0 | Reconnect on Discord PID/device changes | 009 | 10-cycle test |
| LL-011 | P0 | Build VAD/stable-prefix state machine | 008 | regression tests |
| LL-012 | P0 | Bounded queues + stale tentative jobs | 011 | load + failure test |
| LL-013 | P0 | 30-min soak instrumentation | 012+009 | p50/p95 report |
| LL-014 | P1 | Custom glossary & export opt-in | 013 | user acceptance |
| LL-015 | P0 release | Secure localhost session token+WS Origin | 002+009 | threat tests |
| LL-016 | P1 | Package native+Python+web offline | 015 | clean Win11 smoke test |
| LL-017 | P2 | Nemotron vs Whisper experiment | 013 | side-by-side benchmark |

## Mandatory anti-pattern review
- Any claims that system loopback equals Discord-only?
- Any UI control that is inert?
- Any fake translated demo passed off as real model output?
- Any infinite queue or unhandled websocket disconnect?
- Any external request/analytics/fonts when offline?
- Any accidental recording to disk?
- Any version targets net8.0 or net9.0?
- Any undocumented third-party model weights shipped in ZIP?
