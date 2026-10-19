# Owner rulings — 2026-10-01

## Local model may run across GPU and system RAM (reverses the GPU-only ruling of 2026-08-24)

Given by the owner in a Claude Code session: "it can run on gpu and ram ... new rule".

- The standing local model is now **gpt-oss:20b** (13 GB, MoE). The owner chose it and asked that
  all Ollama routing point to it. Measured on the RTX 3080 10 GB: about 19 tok/s,
  41%/59% CPU/GPU split.
- At the owner's request, qwen3:30b-a3b and qwen3:8b were removed from Ollama to free space.
- `config.yaml` `model:` is now `gpt-oss:20b`. Cascade `config.json` entries `local-llama31`
  and `local-qwen3-30b` now point at it. The old files are kept as `*.pre-gptoss`.
- `src/pick_model.py` has `RESIDENT_ONLY = False`. A partly offloaded model is no longer refused.
