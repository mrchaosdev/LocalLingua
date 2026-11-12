# Implementation evidence — 2026-11-12

Tests are DEFERRED at the owner's explicit request (laptop development). No milestone acceptance gate is passed by this report. Historical kit test results in BUILD_VERIFICATION.md are not results from this session.

Environment: Windows build 26200, .NET SDK 8.0.421 only; Python 3.12.10; Node 24.16.0. Python launcher reports no registered Python. `nvidia-smi` and `gh` not found on PATH. Target remains .NET 10 / Python 3.11 / NVIDIA 12 GB; no framework downgrade.

## M0
Implemented per-language immutable final captions, stale/duplicate revision rejection, SDK selection. Original kit preserved in first commit. npm initially failed: Astryx 0.7.12 requires StyleX ^0.19.0, kit used ^0.16.0; corrected to declared peer dependency.

Pending: pytest, browser/demo rendering, native build and overlay DPI. These have not been executed.

## M1
+ Replaced per-frame resampling with stateful libsoxr streaming resampling; validates complete samples and non-finite floats.
+ Added explicit offline GPU configuration (small.en CUDA int8_float16 + local Qwen 4B Q4_K_M), serialized native ASR calls and disabled implicit Whisper downloads by default.
+ System capture now uses 40ms frames, 800ms bounded queue, eviction counter, stale-frame rejection, connection timeout/retry and WAVEFORMATEXTENSIBLE support.

Not run: audio diagnostic 10 minutes, WAV ASR, Qwen inference, CUDA/VRAM verification. M1 gate remains pending.

## M2
Native process-tree helper and AudioHost supervision implemented. See M2-ISOLATION-ACCEPTANCE.md. Native build, Microsoft sample proof, Discord/YouTube exclusion and restart/device tests all NOT RUN. M2 is a hard release blocker. Subsequent commits are implementation work only; no promotion through acceptance gates.

## M3
Implemented independent capture/ASR/translation workers, 800ms audio work bound, bounded final FIFO queues with explicit overflow/pause, latest-wins partial slots, two-hypothesis stable prefix, generation invalidation on stop, VAD onset/hangover, forced segmentation and source-silence flush. Added optional local Silero ONNX VAD (512-sample windows), bounded P50/P95 service-time samples and backend final-age timings.

Added regression cases for immutable finals per language, slow subscriber gap/replay, silence, and stop during translation. Tests NOT RUN. Existing resampler test updated to flush streaming filter tail. No 30-minute run or GPU measurement. Backend final_age_ms excludes device/capture/UI synchronization; it is NOT end-to-end latency.

## M4
Replaced mock navigation and custom dashboard controls with verified official Astryx components (Button, TextInput, Text, Heading, VStack/HStack). Added Vietnamese labels, dark/light mode, audio meter, service-time diagnostics, caption size, Ctrl+Enter shortcut, explicit TXT export and RAM-only glossary hints. Web auth bridge prepared for M5. Overlay: immutable finals, bounded revision state, correct fragmented UTF-8 handling, size +/- and Ctrl+Up/Down opacity, Esc close, PerMonitorV2 manifest.

Not run: browser rendering, Astryx built-asset doctor, screenshot review, accessibility/keyboard, light/dark contrast, overlay multi-monitor / 125-150% DPI. No UI acceptance claim.

## M5
Implemented random per-session bearer auth, WebSocket first-message auth for browsers, exact Origin/Host checks, single ingest producer, capped subscribers, ingest size/rate limits, HTTP control rate limits and no-store/CSP headers. Local Ollama URLs only, proxy environment disabled, no redirects, model unload on shutdown. Added self-contained .NET tray supervisor candidate, PyInstaller engine entry, native/web/Python packaging recipe and model/offline/update documentation. Fixed broken path characters in original PowerShell launch scripts. Backend serves built local assets; no CDN.

Executed lightweight build/syntax checks (not runtime tests): web TypeScript/Vite build PASS; Astryx doctor 11 pass / 1 warn / 0 fail; Python AST 17 files parsed. All automated/runtime tests remain deferred. Native launcher, frozen engine, CUDA dependency packaging and clean installation are unverified. No installable bundle produced on this laptop. Exact model pin/license inventory and synchronized end-to-end latency instrumentation remain pending.

## GitHub
Owner explicitly selected mrchaosdev. Connected GitHub plugin account is different and does not expose repository creation, so publication uses Git Credential Manager and GitHub REST/Git. No usable laptop GitHub credential was present; device sign-in requested. Repository defaults private. Publication outcome will be appended after authentication.

Additional deferred regression cases: fragmented-stream resampler equivalence, final queue overflow/pause, stale translation result suppression and auth/origin/local-provider restrictions. GitHub checks are workflow_dispatch-only and will not run on push. PowerShell scripts parsed successfully; scripts were not executed for packaging. README and verification ledger now describe the modified implementation rather than historical kit success.
Final review: overlay labels mock/demo content explicitly even on status heartbeats and marks disconnected captions as stale. Final syntax parse covers 18 Python files and all PowerShell scripts; git diff --check passed. These are static checks, not acceptance tests.
