# Realtime audio / ASR / translation — engineering algorithm

## Definitions
- `Audio frame`: 20–60ms PCM from Windows loopback, not a sentence.
- `Rolling ASR window`: ~2.4–4.0 seconds sampled from recent ring buffer, refreshed ~600–900ms in baseline.
- `Utterance`: contiguous audible speech separated by silence (or max-duration segmentation). One unique `utterance_id`.
- `Tentative/partial`: text may be revised with increasing `revision`.
- `Final`: stable text for a finished utterance; never modified without an explicit correction event.
- `caption age`: time since speech segment endpoint, not time since model call.

## Why streaming translation is hard
English negation/completion may come late. Literal 1-word translations oscillate and cause meaning errors. Use **semantic clause batching**: ASR previews quickly, translate only stable clauses after punctuation, stable word boundary, or 0.9–1.5s confirmation; force final translation on speech end with bounded wait. Maintain previous 1–3 *final English* turns as context, never treat raw speaker output as instructions.

## Prototype scheduler, with tunables (NOT claimed measured)
```yaml
capture:
  frame_ms: 40
  sample_rate_native: 48000
  resample_to_hz: 16000
  max_pcm_backlog_ms: 800
vad:
  prototype: rms_energy_threshold  # replace with Silero VAD + hysteresis
  speech_onset_ms: 120
  silence_end_ms: 650
  min_utterance_ms: 350
  max_utterance_ms: 11000
asr:
  rolling_window_ms: 3600
  interval_ms: 850
  overlap_ms: 500
  beam_size: 1
  language: en
translation:
  tentative_min_interval_ms: 1300
  max_input_words: 55
  max_output_tokens: 110
  context_final_utterances: 2
  max_queue_tentative: 1
```

## Robust partial stabilization — to implement/benchmark
1. Collect successive ASR hypotheses for SAME utterance (H_n, H_n+1).
2. Normalize whitespace/casing **for comparison only**, preserve original display text.
3. Find stable common WORD prefix (with punctuation heuristics). Require 2 successive observations for commit.
4. Emit `transcript.partial` when changed (revision++) without committing an unstable suffix.
5. Translate only a stable semantic clause or after a max wait and label result tentative.
6. On silence >650ms, run final ASR on the bounded utterance crop, emit `transcript.final`, then `translation.final` when ready.
7. If a new utterance begins while final translation is still busy, prioritize latest caption while preserving committed ordering in history.
8. Never turn absence of speech into hallucinated captions; gate on energy/VAD and avoid language detection for other languages in v1.

## Queue discipline
**Capture queue** (bytes): bounded by ~0.8s; on overload drop oldest raw frames and increment `audio_dropped_frames`; do not block capture callback.
**ASR work**: at most one model inference at a time; stale rolling candidates superseded; final utterance jobs can be prioritized over stale partials.
**Translation tentative**: latest-wins per utterance; keep `revision`, generation ID, `deadline`; ignore output from older revisions.
**Translation final**: bounded FIFO with explicit visible overflow error, never silently pretend all speech has been translated.
**UI subscriber**: per-connection bounded send queue; on slow UI drop partials first and send status about backlog; finalized messages not silently erased from history.

## Revision protocol
```json
{
  "type": "translation.partial",
  "utterance_id": "abc-0001",
  "revision": 4,
  "is_final": false,
  "english": "We will launch but not yet",
  "vietnamese": "Chúng tôi sẽ ra mắt, nhưng chưa phải lúc này.",
  "created_at_ms": 1794470000000
}
```
If UI already saw revision 5, it MUST ignore revision 4. Final is immutable. Do NOT display raw `<think>` tags or assistant preambles from LLM.

## Segmenting utterances under uninterrupted speech
Set forced flush every ~7–11s or at stable punctuation/clause boundary. Back-to-back merged segments must have unique IDs, contiguous timestamps, and ≤0.5s context overlap for ASR. Align overlapping words by timestamp where available, else use token-level LCS de-dup. Long unbroken talk cannot be held until speaker fully stops.

## Timestamp plan and latency budget
Track: `capture_sample_start/end`, `ingest_t`, `vad_onset_t`, `asr_request_t`, `asr_result_t`, `translate_request_t`, `translate_result_t`, `ui_render_t`. `perf_counter()` is safe for intervals in the same process. Cross-process capture→render latency needs explicit synchronization or audio reference test fixture.

SLO experiments:
- P50 first intelligible *Vietnamese partial* ≤2s relative to speech material needed to translate.
- P95 final Vietnamese caption ≤5s after utterance end, on 30-min one-person normal-load test.
- P99 capture queue <0.8s; no growing lag trend; VRAM stable and no inference memory leak.
- Track separate trade-off: word error rate (WER), translated meaning correctness, entity/number/negation accuracy.

These are TARGETS, not present system capabilities.

## Negative cases
- Discord audio stops for 30s: do not emit silence hallucinations.
- Interrupted speaker changes direction: revise tentative translation, final must reflect negation.
- Audio overlap: show an ambiguous caption, do not assert speaker name.
- Vietnamese voice from another program: process-only capture MUST exclude it, don't auto-translate 50 languages.
- ASR GPU OOM: explicit failed state + optional CPU fallback with warning; no hidden infinite retry.
- 6 hours in background: idle VAD should preserve resources; audio capture can be paused.
- Model outputs a malicious command: treat it as QUOTED AUDIO CONTENT, not a system instruction.

## Production improvements beyond scaffold
The starter engine demonstrates the protocol and a rolling ASR path, but lacks validated production VAD/hysteresis, sample-accurate streaming resampling, hard deadlines, real latency sync and process isolation. Treat these as milestone deliverables rather than done.
