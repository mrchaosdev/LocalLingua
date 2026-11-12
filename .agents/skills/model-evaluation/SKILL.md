---
name: model-evaluation
description: Evaluate Whisper, Nemotron, Qwen and TranslateGemma on local NVIDIA 12GB machine without ungrounded performance claims.
---
# Skill: Model evaluation

Read `docs/02-STACK-AND-MODELS.md`, `docs/08-TESTING-BENCHMARK.md`. Record exact model repo/revision, GGUF file quantization, licenses, driver/CUDA/cuDNN, Python, GPU and free VRAM. Use identical source corpus; compare EN WER, critical names, negation, dates/numbers, VI meaning score, first partial and final caption age, p50/p95 latency, VRAM and backlog under 30min run. Never infer Windows compatibility from an HF model card. Never use external APIs with private audio unless user grants permission. Produce `reports/benchmark-YYYYMMDD.md` with raw anonymized timing CSV and clear failures.
