> CURRENT IMPLEMENTATION: the original kit text below is preserved as design/history. Source completion is described in docs/16-COMPLETE-IMPLEMENTATION.md and contracts/audio-frame-v2.md. Runtime acceptance remains unverified by user request.

# Windows 11 audio capture — critical implementation reference

## Source isolation is the first difficult OS task
- **M0/M1**: `NAudio.Wave.WasapiLoopbackCapture` can capture *all audio mixed at one output endpoint* (e.g. Discord + YouTube). This is a useful smoke test ONLY.
- **M2 release gate**: Windows **Application Loopback** activation can target a process tree using `ActivateAudioInterfaceAsync`, `AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK`, `AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS` and `PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE`.
- Do **not** claim NAudio `WasapiLoopbackCapture` by itself can select a PID. Verify behavior of any 3rd party wrapper before adopting.
- Official sample: https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/ApplicationLoopback; requires Windows 10 build 20348+ and works on supported Windows 11.

## Process tree plan
1. Discover running `Discord.exe` root and audio-related subprocesses, inspect process ancestry. Multi-process Electron apps can restart children; do not arbitrarily choose first PID.
2. Select confirmed root PID, include descendants with Windows process-loopback API. If separation fails, fall back with red **Whole system audio** warning, never silently.
3. Show test signal: play YouTube audio with Discord muted → captured signal should be silent; have somebody speak Discord while YouTube plays → captured should contain Discord only.
4. Switch Discord output device or restart app → re-resolve process tree and reinitialize capture; warn user when audio source lost.
5. Release COM resources and audio clients on stop. Capture thread must not block on WebSocket.

## Audio format contract
- Capture host sends JSON `audio.format` before raw frames:
  `{ "type":"audio.format", "sample_rate":48000, "channels":2, "sample_format":"float32" }`.
- Then sends raw little-endian interleaved PCM bytes, **not WAV file headers**; backend validates format and normalizes.
- Capture original sample clock, sequence & dropped sample counts need strengthening after prototype to obtain reliable lag metrics.
- Resample to 16kHz mono with a **stateful polyphase resampler** in production; one-frame-independent scipy resampling introduces boundary artifacts. Starter uses simple frame resampling for proof only.

## Discord and privacy
No Discord user token, no selfbot. Native output capture does not need bot account or channel permissions. Respect Discord terms and local law; clearly show listening status and seek consent before recording or exporting others' speech. Automatic transcripts in memory are still processed personal data; no silent background recording.

## Failure matrix
| Symptom | Hypothesis | Verify |
|---|---|---|
| No audio while Discord talks | Wrong render device or process | Check Windows mixer output, process tree, RMS counter |
| Music transcribed | Whole-system capture, no source isolation | Separate YouTube vs Discord with A/B test |
| Only own voice transcribed | Capturing microphone instead of render loopback | Ensure output loopback, not input mic |
| Audio stutters | Capture callback performing inference or blocking I/O | Bounded channel, move send to separate async worker |
| Caption latency grows | Unbounded audio/translation queue | Monitor queue depth and audio age |
| Works once then not | Discord process restarted, output device switched | Re-enumerate and reinit client |

## Technical prototyping sequence
- First run the official Microsoft ApplicationLoopback sample independently writing WAV to prove process isolation. Do not write a managed interop wrapper while basic COM mode is unverified.
- Then port to managed Windows capture service or ship tested native helper with IPC; keep all audio uncompressed only on localhost and in process memory.
- Add UI source dropdown only after both capture modes pass tests. Add per-PID health diagnostic.
