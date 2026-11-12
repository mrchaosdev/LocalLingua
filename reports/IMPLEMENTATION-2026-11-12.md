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
