# API and wire contract v1

## REST
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | — | `{ok,version}` |
| GET | `/api/status` | — | runtime state / backend config / connection count |
| POST | `/api/control` | `{ "mode":"start|pause|stop" }` | state; state changes gate processing, not launch Windows host |
| POST | `/api/demo` | — | starts sample EN/VI subtitles for dashboard demo |

## WebSockets
- `/ws/ingest`: **native host→backend**. First a UTF-8 JSON `audio.format` text message `{type,sample_rate,channels,sample_format}`, then binary little-endian PCM chunks of THAT format. Not multipart, no WAV header.
- `/ws/events`: **backend→UI**, sends JSON `caption` and `status` envelopes. In release require per-run token/Origin controls.

## Sample event
```json
{
 "type": "caption",
 "phase": "translation.final",
 "utterance_id": "ut-01",
 "revision": 3,
 "is_final": true,
 "english": "We will launch next week.",
 "vietnamese": "Chúng tôi sẽ ra mắt vào tuần tới.",
 "created_at_ms": 1794400000000,
 "source": "mock"
}
```
Other phases: `transcript.partial`, `transcript.final`, `translation.partial`, `translation.final`. During model failure event `type:error` with `code`, `message` (no raw voice). `type:status` with `capture_connected` etc.

## Client rules
- `utterance_id` identifies independent utterances.
- `revision` monotonically increases per ID. Ignore older revisions.
- `is_final` means immutable for that event's phase; final Vietnamese supersedes its own prior tentative VI.
- Gaps may exist after overload; show `Degraded` health, not fake continuity.
- UI cannot infer who spoke from mixed audio; no fake speaker IDs.

## Authentication status
Starter intentionally lacks production session tokens (to keep local PoC readable); this is a documented **P0 pre-release security task**, not a secure multiuser network service. Loopback-only binding is mandatory. Avoid CORS wildcard.
