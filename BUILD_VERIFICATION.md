# Build / test verification — actual session 2026-11-12

The original kit's historical test evidence is preserved in the initial Git commit. It is NOT evidence for the modified implementation.

## Executed

- Environment audit: Windows build 26200; .NET SDK 8.0.421 only; Python 3.12.10; Node 24.16.0. Python launcher found no registered interpreters. nvidia-smi/gh not found on PATH.
- npm install: initial peer dependency failure (StyleX ^0.16 incompatible with Astryx ^0.19 peer). Corrected; 171 packages installed, npm reported 0 vulnerabilities at installation.
- Official Astryx CLI: init, component Button/Card/VStack/Text/TextInput, docs layout.
- npm.cmd run build: PASS, TypeScript and Vite 6.4.6, 2316 modules transformed. Main JS 526.14 kB; Vite warned about chunk size >500kB.
- Astryx doctor --built dist: exit 0; 11 pass, 1 warning, 0 failures. Warning: Windows PATH CLI shim identity; commands were invoked with npx.cmd @astryxdesign/cli. Built assets contain Astryx. Source purity and visual correctness were not inspected by this command.
- Python AST parse: 18 source/test files parsed successfully. This does not import dependencies or execute tests.

## NOT executed

At the owner's request, all automated/runtime acceptance tests are deferred on this laptop: pytest, browser/demo/WebSocket integration, .NET builds/GUI, C++ process capture build, real audio, GPU inference, model quality, isolation, restart/device matrix, 30-minute soak, offline/clean-PC packaging.

No model downloaded, no real meeting audio captured, no GPU/VRAM or latency measurement. M0–M5 acceptance remains PENDING. See reports/IMPLEMENTATION-2026-11-12.md for changes by milestone and reports/M2-ISOLATION-ACCEPTANCE.md for the hard isolation gate.

## v0.4 source-completion continuation — tests NOT RUN

The owner explicitly requested finishing the remaining code without testing. Current source coverage is mapped in docs/16-COMPLETE-IMPLEMENTATION.md. No milestone runtime gate is marked passed.

Executed static checks only:

- `npx.cmd tsc --noEmit`: exit 0. No browser/app started, no test runner.
- Python `ast.parse`: 28 Python files parsed, with no application imports or function execution.
- PowerShell AST parser: all scripts parsed; setup/packaging scripts not executed.
- `node --check scripts/collect-web-licenses.mjs`: exit 0, syntax only.
- JSON contracts parsed and `git diff --check` reviewed.
- Official Astryx Selector/Switch props read via installed CLI. Ollama local-only/preload/show behavior checked against primary API docs/source.

NOT executed: pytest, native/.NET compilation, GUI launch, AI inference, model download/import, capture, installer packaging or 30-minute benchmark. Earlier web build/Astryx doctor results above belong to the earlier implementation; they are not new runtime verification for this continuation.

The current laptop still lacks the target .NET 10/Python 3.11/GPU prerequisites established in the initial audit. Target versions were preserved. Source artifacts include a portable/installer recipe; no binary installer was produced.
