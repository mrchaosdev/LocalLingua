---
name: realtime-audio
description: Implement and validate bounded Windows-to-ASR realtime audio ingest, VAD and partial/final utterance logic in LocalLingua.
---
# Skill: LocalLingua realtime audio

## Required reading
`docs/04-REALTIME-ENGINE.md`, `docs/06-WINDOWS-CAPTURE.md`, `docs/11-CONTRACTS.md`, `docs/08-TESTING-BENCHMARK.md`.

## Workflow
1. Verify genuine audio format and process-tree capture capability; never confuse endpoint and process.
2. Use producer/consumer separation; send callback bytes to a bounded queue, no network I/O on WASAPI callback thread.
3. Convert only supported PCM types (float32/pcm16) to 16 kHz mono; a stateful resampler is mandatory for production quality.
4. Add VAD onset/off hysteresis, max utterance flush and silence reset; test 0-RMS, music, intermittent quiet voices.
5. Add stable-prefix and revision counters for partial ASR. Final event only once per utterance.
6. Drop stale partial translations when overloaded, do not drop finalized speech silently.
7. Prove with recorded permission-cleared 30 min English and emit actual metrics.

## Acceptance
ASR runs off capture thread; bounded queues; no growing backlog; unique segment ids; meaningful partial/final; Windows Discord isolation test pass.

## Do not
Do not call a 20 ms chunk a translation result. Do not claim 'subsecond realtime' because model input chunks can be 80 ms. Do not invent a speaker name. Do not dump private audio to disk.
