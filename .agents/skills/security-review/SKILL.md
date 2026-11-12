---
name: security-review
description: Harden local capture control, WebSocket channels, offline model behavior and privacy-sensitive defaults before LocalLingua personal release.
---
# Skill: Security review

Read `docs/07-SECURITY-PRIVACY.md`. Harden localhost channel against malicious pages and other local processes: session tokens, WS Origin, restrictive CORS, bind only localhost, single producer and rate limits. Turn off logs carrying transcripts, audio capture to disk, or external telemetry. Explicit opt-in for exporting. Treat voice transcript as untrusted data, never as tool commands. Review dependency licenses and no bundled model weights. Report residual risks and verify no network calls in offline operation.
