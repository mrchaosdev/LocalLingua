# LocalLingua kit — validation record (2026-11-12)

## Successfully verified in this environment
- ZIP file generation and file-structure JSON schema validation.
- Python code AST syntax check.
- Python API, audio formatting, stable prefix, revision gate, translation-result sanitization and demo WebSocket tests: **10 passed** with `python -m pytest -q`.
- Package and Astryx versions cross-checked with official web documentation; Astryx `0.7.12` pinned consistently to match its published release group.

## NOT verified here (must be done on target Windows 11 machine)
- `dotnet build` / .NET 10 WPF overlay: runtime SDK unavailable in build container.
- `npm install` / `npm run build`: registry DNS inaccessible from build container (`EAI_AGAIN`), therefore React TypeScript compile not proven.
- NAudio and application-specific Windows loopback: cannot test Windows WASAPI from Linux container.
- Real GPU faster-whisper or Qwen/TranslateGemma inference: no target GPU/model weights provided.
- Latency, 30-minute soak test, memory, ASR quality and translation quality: **not measured**.
- True Discord-only process capture: **not yet coded**, explicitly mandatory milestone M2.
- Release-grade security (session token, Origin restriction) and offline packaged installer: not implemented.

## Honest scope
This ZIP is a high-detail design/agent instruction bundle **plus a starter codebase**. It is not a completed fully tested desktop product. Run milestones in order; do not bypass M2/M3 gates or claim realtime SLO without measured data.
