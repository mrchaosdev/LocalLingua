# Third-party components

LocalLingua application sources are provided for the owner's personal build. Model weights and the Ollama application are not redistributed by this installer.

- .NET runtime / Windows Desktop runtime: Microsoft, MIT; runtime distribution notices apply. https://github.com/dotnet/runtime and https://github.com/dotnet/wpf
- NAudio: Mark Heath / contributors, MIT. https://github.com/naudio/NAudio
- Windows Application Loopback API implementation reference: Microsoft Windows-classic-samples, MIT. https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/ApplicationLoopback
- Astryx: Meta / contributors, MIT. https://github.com/meta/astryx
- React: Meta / contributors, MIT. https://github.com/facebook/react
- Python and dependencies: complete installed distribution metadata and available license files are collected into notices/python during packaging.
- Installed JavaScript package licenses: collected into notices/web. NuGet metadata and available license/notice files: notices/native.

Model download inventory records upstream repository, immutable revision, local SHA256 and license declaration. Qwen3-4B-GGUF uses Apache-2.0; faster-whisper-small.en and Silero declare MIT. Actual model license files/cards are downloaded alongside their weights, outside the application installer.

Generated inventories describe the exact build environment. Missing upstream license files must be resolved before redistribution; a declared SPDX identifier does not replace required license text.
