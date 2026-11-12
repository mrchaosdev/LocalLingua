# M2 isolation acceptance — NOT RUN

Implementation: native C++ Windows process loopback with include-target-process-tree, official Microsoft API/sample reference. No managed COM wrapper before native proof. stdout PCM replaces sample WAV retention. Automatically selects a unique Discord.exe root by parent ancestry; multiple roots fail visibly. Restart is handled by AudioHost re-launch/re-enumeration, never by automatic whole-system fallback.

Build requires VS 2022+ C++ tools, CMake, Windows SDK with audioclientactivationparams.h. Run scripts/build-process-capture.ps1, copy the Release helper alongside AudioHost.exe. Use --system-diagnostic explicitly for M1.

Target PC evidence to record:

| Case | Result | Captured RMS / observation |
|---|---|---|
| YouTube only, Discord silent | NOT RUN | |
| Discord only | NOT RUN | |
| Both simultaneous | NOT RUN | |
| Discord restart | NOT RUN | recovery seconds |
| Output device switch | NOT RUN | recovery seconds |
| Process lost / no system fallback | NOT RUN | |

Known limits: only stable Discord.exe naming supported; Canary/PTB not selected. Packet drops currently logged on helper stderr, not synchronized capture-clock metrics. Native helper has not been built on this laptop. Hard release blocker remains open.

Reference: https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/ApplicationLoopback
