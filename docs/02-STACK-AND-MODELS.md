# Full stack / model sources and downloads

Verified 12 Nov 2026. **Do not confuse a Hugging Face model page with a compatible runtime/quantized artifact**. Follow the model card and license. Models are NOT included in this ZIP (gigabytes and licensing).

## Application
| Layer | Version/option | Purpose |
|---|---|---|
| OS | Windows 11 x64 | App-specific WASAPI capture |
| Capture host | C# .NET 10 LTS + NAudio for system mix POC | Audio source normalization / native integration |
| Release process capture | Microsoft Windows Application Loopback sample (C++/COM) or verified C# wrapper | Exclude other applications |
| Overlay | C# .NET 10 WPF | Topmost click-through-capable translucent captions |
| Web | React 19, TypeScript, Vite | UI dev, locally served dashboard |
| Design system | `@astryxdesign/core`, `@astryxdesign/theme-neutral`, `@stylexjs/stylex`, `@astryxdesign/cli` | Official Meta Astryx (MIT) |
| AI API | Python 3.11, FastAPI, uvicorn, WebSocket | Local control & stream protocol |
| ASR | faster-whisper / CTranslate2 | EN streaming-like rolling baseline |
| Audio gating | Silero VAD optional, prototype simple RMS energy gate only | Avoid inference during silence |
| Translation | Qwen3 4B GGUF Q4_K_M via Ollama or llama.cpp local | EN→VI text generation |
| Packaging | .NET publish + local Python build, future installer | User PC only |
| Database | No DB v1, optional SQLite for opted-in history | Privacy and simplicity |

## 1. Hugging Face official links
| Role | Model / URL | License visible on model page | Notes |
|---|---|---|---|
| ASR baseline | https://huggingface.co/Systran/faster-whisper-small.en | MIT | Optimized CTranslate2 small.en checkpoint |
| ASR challenger | https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b | NVIDIA Open Model License | Real cache-aware streaming; Windows integration gate |
| Translator baseline (official quantization) | https://huggingface.co/Qwen/Qwen3-4B-GGUF | Apache 2.0 | Official GGUF Q4_K_M usable with llama.cpp/Ollama |
| Translator original | https://huggingface.co/Qwen/Qwen3-4B | Apache 2.0 | Unquantized model: not the same as GPU Q4 runtime |
| Translation challenger | https://huggingface.co/google/translategemma-4b-it | Gemma license | Needs supported Transformers runtime; not interchangeable GGUF |
| Research-only small translation | https://huggingface.co/facebook/nllb-200-distilled-600M | CC BY-NC 4.0 | **Noncommercial / research use**; not default for redistributable commercial app |

## 2. Download commands

```powershell
# Base: https://huggingface.co/docs/huggingface_hub/en/guides/cli
py -3.11 -m pip install -U huggingface_hub
# Optional: inspect cache or materialize model to a local folder
hf download Systran/faster-whisper-small.en --local-dir "$env:USERPROFILE\Models\faster-whisper-small.en"

# Ollama easiest route for official Qwen GGUF from Hugging Face:
# Install Ollama from https://ollama.com/download/windows, then:
ollama run hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
# NOTE: verify actual installed model ID using `ollama list` and copy it into OLLAMA_MODEL.

# Or with llama.cpp installed from WinGet:
winget install llama.cpp
llama serve -hf Qwen/Qwen3-4B-GGUF:Q4_K_M
# Exact binary CLI name/flags should be verified on installed llama.cpp version.

# Research-only downloads (do not download until needed)
hf download google/translategemma-4b-it --local-dir "$env:USERPROFILE\Models\translategemma-4b-it"
hf download nvidia/nemotron-speech-streaming-en-0.6b --local-dir "$env:USERPROFILE\Models\nemotron-speech-streaming"
```

For the real ASR backend, first install `pip install faster-whisper` inside the engine venv and verify the official CUDA/cuDNN prerequisites. For Whisper, `WhisperModel('small.en', device='cuda', compute_type='int8_float16')` automatically fetches the supported checkpoint to the model cache on first run. Use the `model path` if working offline. The Python code defaults to CPU/mock until explicitly changed; **CUDA 12 + cuDNN 9 requirements for current CTranslate2 must be satisfied and benchmarked**; see https://github.com/SYSTRAN/faster-whisper.

## 3. Why Qwen baseline first, TranslateGemma challenger later
- Official Qwen3 GGUF has documented Windows llama.cpp/Ollama path, Q4_K_M available, suitable for a 12GB VRAM experiment.
- Qwen may generate verbose explanations; prompt must demand translation only, `temperature=0`, token cap, /no_think where supported; strip hidden reasoning rather than display it.
- TranslateGemma 4B is translation-focused, but its official base checkpoint is Gemma-family multimodal Transformers, **not** a drop-in `ollama run translategemma:4b` guarantee; must validate runtime, format and license before adopting.
- Model choice requires *actual* benchmarks on short informal Discord conversations (acronyms, negation, fast speech, slang).

## 4. VRAM planning — indicative ONLY
For one NVIDIA 12 GB GPU, a quantized 4B model and a small ASR model *may* coexist, but CUDA buffers, KV cache, fragmentation and desktop apps consume additional space. Verify actual maximum allocated GPU memory with `nvidia-smi` while running both. If OOM, reduce Qwen context, use smaller ASR, reduce model residency, or move one component to CPU. Do not assume 12GB VRAM is fully free.

## 5. ASR choice gate
Compare rolling small.en with genuine streaming Nemotron **only after** basic bridge and UI work. Compare WER, stability, latency, VRAM, model compatibility, setup complexity and continuous-running behavior. Native 80ms audio chunks are NOT an 80ms translated subtitle guarantee.

## 6. Reference tooling
- Microsoft app loopback sample: https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/ApplicationLoopback
- Astryx docs: https://astryx.atmeta.com/docs/getting-started
- Astryx CLI/docs source: https://github.com/meta/astryx
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Silero VAD: https://github.com/snakers4/silero-vad
- NeMo Speech C++: https://github.com/NVIDIA/NeMo-Speech.cpp
- Hugging Face CLI: https://huggingface.co/docs/huggingface_hub/en/guides/cli
- .NET lifecycle: https://dotnet.microsoft.com/en-us/platform/support/policy
