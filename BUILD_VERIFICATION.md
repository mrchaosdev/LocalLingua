# Build / test verification — actual session 2026-11-12

The original kit's historical test evidence is preserved in the initial Git commit. It is NOT evidence for the modified implementation.

## Executed

- Environment audit: Windows build 26200; .NET SDK 8.0.421 only; Python 3.12.10; Node 24.16.0. Python launcher found no registered interpreters. nvidia-smi/gh not found on PATH.
- npm install: initial peer dependency failure (StyleX ^0.16 incompatible with Astryx ^0.19 peer). Corrected; 171 packages installed, npm reported 0 vulnerabilities at installation.
- Official Astryx CLI: init, component Button/Card/VStack/Text/TextInput, docs layout.
- npm.cmd run build: PASS, TypeScript and Vite 6.4.6, 2316 modules transformed. Main JS 526.14 kB; Vite warned about chunk size >500kB.
- Astryx doctor --built dist: exit 0; 11 pass, 1 warning, 0 failures. Warning: Windows PATH CLI shim identity; commands were invoked with npx.cmd @astryxdesign/cli. Built assets contain Astryx. Source purity and visual correctness were not inspected by this command.
- Python AST parse: 17 source/test files parsed successfully. This does not import dependencies or execute tests.

## NOT executed

At the owner's request, all automated/runtime acceptance tests are deferred on this laptop: pytest, browser/demo/WebSocket integration, .NET builds/GUI, C++ process capture build, real audio, GPU inference, model quality, isolation, restart/device matrix, 30-minute soak, offline/clean-PC packaging.

No model downloaded, no real meeting audio captured, no GPU/VRAM or latency measurement. M0–M5 acceptance remains PENDING. See reports/IMPLEMENTATION-2026-11-12.md for changes by milestone and reports/M2-ISOLATION-ACCEPTANCE.md for the hard isolation gate.
