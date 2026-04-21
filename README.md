# FinGuard

**A Lightweight Guard/Verify Wrapper for Safer Financial Assistants**

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Tests: 77 passed](https://img.shields.io/badge/Tests-77%20passed-brightgreen)
[![arXiv](https://img.shields.io/badge/arXiv-XXXX.XXXXX-b31b1b)](https://arxiv.org/abs/XXXX.XXXXX)

## What Is FinGuard?

FinGuard is a two-layer safety wrapper for financial assistants: a pre-generation guard plus a post-generation verifier. It is not a RAG system, a fine-tuned model, or a replacement agent. Instead, FinGuard wraps an existing Hermes-style assistant and improves refusal correctness, numeric traceability, and over-refusal control without modifying the underlying model. We evaluate the same wrapper on Gemma 4 31B and Qwen3.5-27B local model endpoints.

## Pipeline

`docs/pipeline.png` is reserved for the final exported paper figure. Until that asset is added, the pipeline is:

```text
TODO: replace this ASCII placeholder with docs/pipeline.png

User Query
   |
   v
FinGuard Layer (Pre-Generation)
   |  query classification, injection detection, temporal intent
   v
Hermes Agent Core (Unchanged)
   |  local model generation
   v
FinVerify Layer (Post-Generation)
   |  numeric claim checks, source matching, downgrade/disclaimer
   v
Final Response + Structured Metadata
   |
   v
Benchmark Observer
```

## Key Results

| Model | System | Aligned Behavior-Safe | Over-Refusal |
|---|---|---:|---:|
| Gemma 31B | vanilla | 0.933 | 0.019 |
| Gemma 31B | finguard | 0.989 | 0.000 |
| Qwen3.5-27B | vanilla | 0.922 | 0.154 |
| Qwen3.5-27B | finguard | 1.000 | 0.000 |

For full results including the naive RAG baseline and category breakdown, see our paper.

## Quick Start

```bash
git clone https://github.com/DuckTraDo/finguard.git
cd finguard
uv venv venv --python 3.11
source venv/bin/activate  # Windows: venv\Scripts\activate
uv pip install -e ".[dev]"
python -m pytest tests/finguard -q
```

## Reproduce Paper Results

Prerequisites:

- A local llama.cpp, vLLM, or compatible server running at `http://localhost:18080/v1`.
- The endpoint must expose an OpenAI-compatible chat completions API.
- The served model should be Gemma 4 31B or Qwen3.5-27B for direct comparison with the paper.

Run the 90-case local smoke benchmark:

```bash
# Run vanilla baseline (90 cases)
python -m finguard.benchmark_smoke \
  --dataset-path benchmarks/finguard/local_comparison_v3.jsonl \
  --baseline-mode vanilla \
  --run-profile benchmark_local_smoke_profile \
  --output-dir benchmarks/finguard/live_vanilla \
  --limit 90 \
  --max-tokens 192

# Run FinGuard baseline (90 cases)
python -m finguard.benchmark_smoke \
  --dataset-path benchmarks/finguard/local_comparison_v3.jsonl \
  --baseline-mode finguard \
  --run-profile benchmark_local_smoke_profile \
  --output-dir benchmarks/finguard/live_finguard \
  --limit 90 \
  --max-tokens 192
```

Results are written to `benchmarks/finguard/live_*/` as `rows.jsonl` and `summary.json`.

## Project Structure

```text
finguard/
|-- finguard/                 # Core FinGuard package
|   |-- fin_guard.py          # Pre-generation guard layer
|   |-- fin_classifier.py     # Query classification (rule + LLM hybrid)
|   |-- fin_verify.py         # Post-generation verification
|   |-- fin_utils.py          # Source normalization, numeric helpers
|   |-- config.py             # Feature flags and thresholds
|   `-- benchmark_smoke.py    # Benchmark runner
|-- skills/finance/           # Financial skills (Hermes format)
|   |-- fin-source-citation/
|   `-- fin-temporal-awareness/
|-- benchmarks/finguard/      # Benchmark datasets, results, and paper assets
|-- tests/finguard/           # Test suite (77+ tests)
|-- docs/                     # Documentation
|   `-- finguard-behavior-matrix.md
|-- run_agent.py              # Hermes agent with FinGuard hooks
`-- README.md
```

## How It Works

**FinGuard Layer (pre-generation).** FinGuard classifies each query as factual, compliance-sensitive, operational, or injection-like. It detects prompt-injection patterns, extracts temporal intent, and assigns a second-level `expected_behavior` label for compliance-sensitive requests, such as `refuse_with_disclaimer` or `answer_with_disclaimer`.

**FinVerify Layer (post-generation).** FinVerify extracts numeric claims from the model response and checks whether each number is supported by normalized sources. If support is insufficient, it downgrades the certainty of the answer and adds a verification note. For compliance-sensitive answers, it enforces disclaimer behavior before the final response is returned.

**Benchmark Observer.** The observer records both raw and aligned refusal patterns, separating metadata refusal from visible refusal. It also distinguishes behavior-safe outputs from metadata-aligned outputs, which makes it easier to diagnose whether an error is a real unsafe answer or an instrumentation/taxonomy mismatch.

## Citation

```bibtex
@article{lu2026finguard,
  title={FinGuard: A Lightweight Guard/Verify Wrapper for Safer Financial Assistants},
  author={Lu, Yuxin and Lin, Huijia},
  journal={arXiv preprint arXiv:XXXX.XXXXX},
  year={2026}
}
```

## License

MIT License, inherited from Hermes Agent.

## Acknowledgments

FinGuard is built on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research. We add two runtime hooks and a benchmark harness; the Hermes core agent loop is unchanged. See the original Hermes documentation in `docs/hermes-original-README.md`.
