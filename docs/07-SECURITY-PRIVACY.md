> IMPLEMENTATION UPDATE 2026-11-12: the sections below describe the original kit. Current code adds session bearer auth, WebSocket auth/Origin checks and native process capture candidates. See BUILD_VERIFICATION.md and reports/IMPLEMENTATION-2026-11-12.md; runtime security/isolation are NOT verified.

# Threat model, privacy and permissions

## Security goals
- No third-party content service observes private meeting audio/transcript in local mode.
- No external user can invoke audio controls or read transcript over network.
- Audio frame and translated text are ephemeral unless user explicitly exports.
- Remote speaker audio is untrusted text: translated sentences cannot become LLM tool instructions.

## Rules
1. Bind all network listeners to `127.0.0.1`. Do not enable `0.0.0.0` even in examples. If shipping beyond personal PC, add per-session auth token and strong Origin checking; localhost does not imply all local processes are trusted.
2. Use a random per-run session token for `/ws/ingest`, `/ws/events` and `/api/control` before production release, not in starter scaffold (documented limitation). Only local WPF/web clients get this token via secure bridge.
3. Browser CORS: whitelist `http://127.0.0.1:5173` only in dev. Strict Origin validation for WebSocket in release, do not accept arbitrary public websites controlling it.
4. No login/password, Discord auth token, bot token, screen scraping. Never embed HF user tokens in source.
5. Model files: fetch only official sources; review model licenses and pin revision hashes before release. Check raw `*.safetensors`, GGUF and dynamic remote code policies.
6. Audio retention off. `*.wav`, transcripts, screenshots excluded in `.gitignore`; export to explicit user-selected location only.
7. Do not instrument provider telemetry and web analytics. Avoid remotely loaded fonts in packaged offline mode.
8. Warn user that live translation can be wrong about numbers, financial decisions, terms and negation.
9. Log technical metrics but not speech contents by default; debug transcript logging must be opt-in and sanitized.
10. If adding cloud mode later, separate explicit provider approval and clear warning `Dữ liệu có thể được gửi ra ngoài`.

## Threats and mitigations
| Threat | Mitigation |
|---|---|
| Malicious webpage requests localhost | CORS + Origin enforcement + token + content-type restrictions |
| Another local process connects audio WS | Random auth token/OS ACL + single producer lock |
| Discord speaker says "ignore previous instructions" | Treat transcript as data; translation-only prompt, output validation, no tools/actions |
| Disk forensic transcript leakage | No local persistence by default; secure opt-in export |
| LLM hallucinates trading/buy instructions | Show original English alongside Vietnamese, uncertainty notice |
| Model license mismatch | Model registry with exact source, license, revision |
| Unintended other-app audio | Discord-only process loopback gate before release |

## Safeguard status
This ZIP scaffold only enforces some rules (loopback bind, CORS dev, no auto-disk storage); the session-token, stricter WS origin and real Discord isolation are **mandatory release blockers**.
