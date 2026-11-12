# LocalLingua — coding-agent operating contract

You are building a **personal, local-first Windows 11 English→Vietnamese live subtitle companion**. You MUST follow the design and gates in README and docs. Do not invent APIs, model versions, current performance or missing code. Keep build/test evidence.

## Before any code
1. Read `docs/00-DECISIONS.md`, `docs/09-IMPLEMENTATION-PLAN.md`, `docs/04-REALTIME-ENGINE.md`.
2. Read the task-specific skill under `.agents/skills/`.
3. Check environment (`dotnet --info`, `python --version`, `nvidia-smi`, `node --version`, `npm --version`); report absent dependencies. Do not silently downgrade target frameworks.
4. Check Astryx component APIs with `npx @astryxdesign/cli init` and `npx @astryxdesign/cli component <Component>` **after npm install**. Avoid guessing prop names.

## Absolute rules
- Target `net10.0-windows` for .NET projects. No .NET 8/9.
- Source speech is ENGLISH; target captions VIETNAMESE. Don't build two-way interpretation or bot participation.
- Use official Astryx packages (`@astryxdesign/core`, `@astryxdesign/theme-neutral`, `@stylexjs/stylex`), not a made-up Astryx clone. Do not copy images/fonts from the website.
- No external model calls without explicit user opt-in; default loopback network binding `127.0.0.1` only.
- Keep `ASR_BACKEND=mock`, `TRANSLATE_BACKEND=mock` for fast tests; demonstrate real providers only after dependencies verified.
- Start with system loopback to prove audio path; `Discord-only capture` is a separate P0 gate. Do NOT claim whole-system loopback == Discord-isolated capture.
- Do not claim stable realtime from rolling-window Whisper without benchmark. Mark tentative/final semantics.
- Never fabricate an achieved test or publish screenshots as if native functionality were verified.
- No admin Discord token, selfbot, account credential scraping or stealth background recording.
- No audio logging or retention by default; transcript opt-in only.

## Branch / delivery discipline
- Complete one milestone with working test then move on. Each PR: exact files, test invocation and result, risks/open items.
- Add regression tests for audio silence, repeated ASR words, canceled stale translations, reconnect, out-of-order revisions.
- Any UI change must preserve keyboard access, contrast and visual hierarchy.
- Prioritize bounded memory and measurable P50/P95 rather than feature count.
- Keep UI labels human-readable Vietnamese. Use English IDs/code comments where appropriate.

## Definition of done for each milestone
See `docs/08-TESTING-BENCHMARK.md` and `docs/09-IMPLEMENTATION-PLAN.md`. Any unmet gates must be disclosed as TODO, not hidden.
