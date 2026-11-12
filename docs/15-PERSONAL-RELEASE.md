# Personal packaging and installation

The implementation and user workflow are documented in [16-COMPLETE-IMPLEMENTATION.md](16-COMPLETE-IMPLEMENTATION.md). Packaging has source recipes; no installer binary has been built or accepted in this delivery.

## Build prerequisites

Windows 11 x64, .NET 10 SDK, Python 3.11, Node >=22.13, Visual Studio C++ build tools, recent Windows SDK, CMake. Install Inno Setup 6 for an installer. Do not downgrade the target framework to match the development laptop.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package-personal.ps1
powershell -ExecutionPolicy Bypass -File scripts/package-personal.ps1 -Installer
```

Each invocation creates a new timestamped release folder. It builds official Astryx assets, publishes self-contained .NET executables, builds the native process helper, freezes the Python engine including GPU/model-install modules, collects dependency notices/inventories, writes SHA256 hashes and creates a portable ZIP. -Installer additionally invokes Inno Setup for a per-user installer and shortcuts. Existing release folders are not overwritten. The script does not run unit/inference/soak tests.

Python and .NET are bundled. Compatible NVIDIA driver, CUDA/cuDNN and Ollama remain target-PC prerequisites. Model weights are downloaded separately, once, by an explicit dashboard action or scripts/install-models.ps1. Exact downloaded revisions/hashes/license declarations are stored privately in the model inventory. There are no bundled weights or remote inference calls.

## First launch

Run LocalLingua.Launcher.exe. Its tray menu opens dashboard/overlay, retries failed components, opens the official Ollama installation page or quits all owned components. Capture starts idle. Configure sources/models in the dashboard, install models when needed, restart to apply generated local GPU paths, then click Bắt đầu. Demo is explicitly synthetic.

Overlay Ctrl+Alt+L locks/unlocks click-through, Ctrl+Alt+O toggles visibility, Màn hình cycles monitors. Closing the overlay leaves the tray app running; Stop or Pause in the dashboard stops capture. Quit from the tray to stop the application and release models.

## Updating / rollback

Exit the tray app before replacing application files. Install a new version or extract a new portable folder; retain the old folder for rollback. Preferences, geometry, technical metadata and models are stored under LocalAppData/LocalLingua. The installer leaves this user-owned directory when uninstalling. No transcripts or audio are saved automatically. There is no automatic updater.

Binaries are unsigned. Distribution license texts available in the installed dependency packages are collected by the recipe; review generated inventories/missing notices before redistribution. A build or installer cannot certify runtime isolation, GPU compatibility or latency. Those checks were intentionally not run.
