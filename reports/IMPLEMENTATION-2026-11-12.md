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

### Publication completed
Authenticated GitHub account verified as mrchaosdev. Created private repository https://github.com/mrchaosdev/LocalLingua and pushed main successfully. Git reported [new branch] main -> main and configured origin/main tracking. No automated/runtime tests were run; GitHub checks remain manual-only.

## Continuation — v1 code completion, tests explicitly disabled

Owner request: “làm nốt full đi. không cần kiểm thử”, followed by “tiếp đi”. Continued source implementation and publication are authorized. No runtime test, audio capture, AI inference, model download, native build, installer build or benchmark was run.

### M0 / contracts
- Added binary PCM v2 header, source/QPC calibration, source interval and trace fields in caption contracts.
- Event WebSocket now receives bounded render acknowledgements; UI history clears/reconnects and immutable finals remain per language.

### M1 / local models
- Model installer resolves official Whisper/Qwen repositories to immutable revisions, verifies available upstream LFS hashes, saves local SHA256/license inventory and imports local GGUF into Ollama.
- Silero ONNX/license comes from an immutable commit of the official upstream repository.
- Added first-run model download action, local dependency/GPU/model diagnostics, preloading and configurable local paths/CPU/CUDA compute.
- Downloads are explicit, never part of application startup. No downloaded weights or local user configuration enter Git.

### M2 / capture lifecycle
- AudioHost is now an idle daemon; only Start opens WASAPI/native capture. Pause/Stop cancel the source and preserve already-captured final work.
- Added source/endpoint/PID controls, local device/root catalog, selected-PID rebind after a unique Discord restart, default-device recovery and no system fallback.
- Native packets carry sequence, sample position, QPC endpoint and drop/timestamp-validity bits; gaps and timestamp uncertainty are surfaced.

### M3 / realtime
- Fixed resampler-tail handling, bounded queue drain on pause, worker recovery, cancellation of superseded tentative translation, bounded final queues and no concurrent native ASR.
- Added actual source-clock mapping, resampler delay accounting, browser/WPF render acknowledgements, first-VI-partial/final-render distributions and 30-minute first/last-window lag instrumentation.
- Metrics/technical trace export contains no speech/audio, includes real model/GPU/profile metadata when explicitly requested; no measurements are fabricated.

### M4 / complete controls
- Official Astryx Selector/settings panels, matched current EN/VI, history/search, glossary list/delete and explicit TXT/MD/SRT exports. SRT requires source timestamps; file picker is used where supported.
- Added WPF global lock/unlock/visibility hotkeys, click-through safety, monitor cycling, remembered geometry, live font/opacity/English preferences and English display when translation is pending/unavailable.
- Added visible bounded-history eviction count and per-tab token refresh support.

### M5 / distribution and recovery
- Added per-user Inno Setup installer source, portable ZIP generation, Python/JS/NuGet notice collectors and dependency inventories.
- Added local Ollama startup/ownership, failed-component retry, abnormal overlay recovery, technical rotating metadata logs without log-message bodies, and robust prerequisite reporting.
- Rewrote current usage/coverage documentation; older kit documents are explicitly identified as historical.

Static checks in this continuation: TypeScript no-emit compile, Python AST parse, PowerShell parser and Node script syntax checks only. Commands/results are recorded in BUILD_VERIFICATION.md. Tests remain unexecuted, including the updated regression sources. Source coverage is not runtime acceptance. See docs/16-COMPLETE-IMPLEMENTATION.md for the requirement-to-code matrix.

Final static check outputs: TypeScript exit 0; Python AST 28 files; PowerShell parse successful; Node --check successful. No runtime/test command executed. Local Ollama provider additionally validates that the configured model has local GGUF weights and no remote host/model metadata before any subtitle text is submitted. Owned Ollama server disables cloud features.
