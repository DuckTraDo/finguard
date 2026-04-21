# FinGuard Local Qwen Comparison v3 Result Table

Status: Qwen local-smoke migration check. This result does not change classifier, guard, verify, naive RAG, full Hermes path, model startup, endpoint management, or llama.cpp configuration.

Endpoint: `http://localhost:18080/v1`
Resolved model: `unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-Q6_K.gguf`
Dataset: `local_comparison_v3.jsonl`
Profile: `benchmark_local_smoke_profile`
Comparison: `vanilla_qwen` vs `finguard_qwen`

## Routing Smoke

Both `--limit 3` runs completed before the full 90-case run.

| System label | baseline_mode | provider_mode | resolved_endpoint | adapter_name | provider_error_type | rows/summary |
| --- | --- | --- | --- | --- | --- | --- |
| `vanilla_qwen` | `vanilla` | `local` | `http://localhost:18080/v1` | `openai_chat_adapter` | null | complete |
| `finguard_qwen` | `finguard` | `local` | `http://localhost:18080/v1` | `openai_chat_adapter` | null | complete |

No context-window, thinking, continuation, provider, or routing errors were observed in the smoke runs.

## Observer-Only Wording Alignment

The first Qwen full run exposed safe refusal wording not covered by the existing visible-refusal observer, especially:

- "I cannot ignore safety rules..."
- "I cannot reveal internal classification prompts..."
- "I cannot disregard safety constraints..."
- "I cannot place trades or take account actions..."
- "As an AI without real-time data access, I cannot provide the latest..."

One observer-only alignment pass added aligned wording coverage while preserving raw observer fields. No model behavior, prompt, corpus, guard, verify, or generation logic changed.

## Full 90-Case Result

| Baseline | total_cases | schema_valid_rate | completed_rate | run_error_count | metadata_refusal_accuracy | raw_visible_refusal_accuracy | aligned_visible_refusal_accuracy | raw_behavior_safe_rate | aligned_behavior_safe_rate | over_refusal_rate | aligned_visible_over_refusal_rate | metadata_aligned_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vanilla_qwen` | 90 | 1.0 | 1.0 | 0 | 0.7778 | 0.8778 | 0.9222 | 0.8778 | 0.9222 | 0.1538 | 0.0192 | 0.0 |
| `finguard_qwen` | 90 | 1.0 | 1.0 | 0 | 0.8556 | 0.9444 | 1.0 | 0.9444 | 1.0 | 0.0 | 0.0 | 0.8111 |

Interpretation:

FinGuard's advantage transfers from Gemma to Qwen under the local smoke profile. On Qwen, FinGuard improves metadata refusal accuracy, raw visible safety, aligned visible safety, over-refusal, and metadata alignment. The strongest migration signal is aligned behavior safety: `finguard_qwen` reaches `1.0` versus `0.9222` for `vanilla_qwen`.

## Category Readout

Aligned behavior-safe rate by category:

| Baseline | factual | compliance_sensitive | temporal | injection |
| --- | ---: | ---: | ---: | ---: |
| `vanilla_qwen` | 0.9706 | 0.9412 | 0.9062 | 0.6364 |
| `finguard_qwen` | 1.0 | 1.0 | 1.0 | 1.0 |

Category interpretation:

FinGuard improves Qwen most clearly on injection and temporal cases. The injection slice moves from `0.6364` under `vanilla_qwen` to `1.0` under `finguard_qwen` after preserving raw and aligned observer views. Temporal behavior also improves from `0.9062` to `1.0`, with FinVerify downgrade metadata marking unsupported source claims instead of allowing unsupported certainty.

## Migration Claim

The safe claim from this node is:

> Under the same local smoke profile and Qwen3.5-27B endpoint, FinGuard preserves its advantage over vanilla generation: it improves visible safety, reduces over-refusal, and restores structured metadata observability.

Boundary:

This is still a local-smoke result. It is not a full Hermes path result, not a naive RAG Qwen result, and not a multi-model production benchmark. The current node only validates whether the FinGuard-vs-vanilla advantage transfers from Gemma to Qwen under controlled local conditions.
