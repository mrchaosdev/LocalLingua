# Product Requirements — detailed

## Problem statement
The user joins English-speaking Discord Voice Channels/Stages (including Web3 communities), cannot understand fast native conversations, and needs readable Vietnamese meaning quickly without asking other participants to change behavior. The product should not create meeting rooms or impersonate a Discord bot.

## Primary persona
One Vietnamese Windows 11 desktop user (32 GB system RAM, 12 GB NVIDIA VRAM), developer/security background. Fluent understanding not assumed. Works with Discord desktop, headset; may simultaneously use Chrome and a secondary monitor.

## Jobs to be done
1. Hear the remote English speaker normally without a delayed audio loop.
2. Read concise Vietnamese translation near realtime, including crypto/Web3 technical vocabulary.
3. Recognize whether a caption is preliminary or final; not lose already-confirmed information.
4. Move a transparent caption overlay over any desktop window, or read a dedicated pop-out/window/browser.
5. Diagnose slow GPU/model processing and change profile without programming.
6. Optionally review/export text **only when explicitly enabled**.

## Functional requirements
| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| F01 | P0 | Listen to system output on Win11 for PoC | Audible external English yields PCM frames and original playback unchanged |
| F02 | P0 release | Isolate Discord process tree | Non-Discord YouTube audio NEVER enters captured stream in test |
| F03 | P0 | English ASR near-real-time | Emits partial/final events with proper segment ID, order and timestamps |
| F04 | P0 | English→Vietnamese translation | Meaning/negation/amounts/terms not systematically corrupted |
| F05 | P0 | Realtime bounded queues | 30 min test does not accrue infinite lag; stale partial jobs dropped |
| F06 | P0 | Captions window | Always on top, drag, resize (later), selectable size, contrast |
| F07 | P0 | Web dashboard | Current sentence, history, source selection/status, performance |
| F08 | P0 | Offline after models installed | Network disconnected still captions, no calls to external APIs |
| F09 | P0 | Start/Pause/Stop controls | State machine enforced, no hidden capture while stopped |
| F10 | P0 | Privacy | Explicit signal when recording/capture active, no automatic disk storage |
| F11 | P1 | Custom glossary | User-controlled term mapping for Web3/crypto acronyms and entities |
| F12 | P1 | Export | TXT/MD/SRT optional, local path selected by user |
| F13 | P1 | Adaptive performance profile | Fast/Balanced/Quality with measured settings |
| F14 | P1 | Process/device reconnect | Handles Discord quit/reopen, headset switch, engine restart |
| F15 | P2 | Speaker labels | Best effort only; never infer speaker identity falsely |

## Nonfunctional requirements
- P95 backend frame ingest under 100ms on unloaded system; capture must not block translation.
- P50 **first meaningful Vietnamese partial** target ≤2 seconds after relevant speech begins; P95 of finalized caption target ≤5 seconds after end-of-utterance. These targets are experimental and may need adjustment.
- 30-minute English test: no rising end-to-end lag or unbounded memory; FPS and average acoustic delays recorded.
- Single-machine, no background server exposed beyond `127.0.0.1`; one active capture producer, multiple local UI subscribers.
- Accessibility: WCAG-style readable contrast, keyboard interactions, screen-reader labels in dashboard. No forced unreadable animation.
- CPU/GPU compute does not interfere with Discord playback or push the host into sustained VRAM OOM.

## Out-of-scope v1
- Discord OAuth/selfbot/API chat scraping, recording people covertly, server administrator requirements.
- Vietnamese speech output / AI voice dubbing (causes lag and sound collision).
- Auto language detection / bidirectional speech translation; support dozens of simultaneous speakers.
- Meeting bot, hosted SaaS, payments, user accounts, synchronization, Kubernetes, RAG/vector DB.

## Journey / user flows
**First-run:** install → download model(s) with license info → hardware/driver diagnostic → loopback test → select Discord → display styles → calibrate speech-to-caption delay → enter meeting.

**Normal:** open LocalLingua → check ASR/translation/Discord indicators → Start → partial (dim) → final (high contrast) → Pause or Stop → explicit Export if needed.

**Failure:** capture not detected → helper describes PID/endpoint/audio mixer; ASR unavailable → show English text status; translator unavailable → show English text and error instead of bogus Vietnamese.

**Negative scenarios:** disconnections, 30s silence, 2 voices overlapping, speaker interrupts, rapidly switching device, extremely quiet speech, sudden music, fake command spoken by participants, malicious website tab.
