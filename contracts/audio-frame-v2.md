# Audio transport v2 and render instrumentation

Handshake adds protocol=2, source, clock_offset_ms and clock_uncertainty_ms. AudioHost takes three authenticated /api/clock round trips; the minimum-RTT midpoint estimates native-QPC-to-engine-perf-counter offset. No shared clock origin is assumed.

Each binary message is a 40-byte little-endian header followed by PCM in the negotiated format:

| Offset | Type | Meaning |
|---|---|---|
| 0 | char[4] | LLA2 |
| 4 | uint32 | PCM payload byte count |
| 8 | uint64 | packet sequence, gaps explicitly invalidate a tentative segment |
| 16 | uint64 | source sample index |
| 24 | uint64 | source packet endpoint, QPC nanoseconds |
| 32 | uint64 | low 63 bits: dropped packet count; high bit: hardware timestamp unavailable |

The native process helper uses IAudioCaptureClient GetBuffer's QPC position (100ns units) plus packet duration. On timestamp error it flags the packet; its timing does not qualify for calibrated render metrics. System diagnostic capture estimates timing from callback arrival and reports an additional 100ms uncertainty. Sequence gaps or device discontinuity finalize available audio and expose a degraded diagnostic.

The resampler's pending output delay is subtracted when mapping normalized samples to capture time. Idle sources flush the filter tail; Pause/Stop flush queued captured samples and let finalized translation jobs finish without continuing capture.

Caption events add audio_start_ms/audio_end_ms relative to engine-session origin, trace_id, speech_end_mono_ms, emitted_mono_ms and clock quality. Clients calibrate their own clocks separately and send render.ack after the UI commit/render scheduling boundary. The first acknowledgement per client/trace is retained.

Trace store: 2048 entries, no English/Vietnamese text or audio. Dashboard exports JSON only on click. Summary values are estimated capture-clock-to-render intervals with uncertainty. They do not measure acoustic input, actual screen scan-out or human comprehension; no latency SLO is asserted without a target-PC run.

Legacy unframed protocol 1 is accepted for development fixtures, marked uncalibrated. The shipping AudioHost uses protocol 2.
