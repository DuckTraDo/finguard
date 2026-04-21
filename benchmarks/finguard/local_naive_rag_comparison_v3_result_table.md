# FinGuard Local Naive RAG Comparison v3 Result Table

Status: first same-scale local-smoke three-way comparison for `vanilla`, `finguard`, and `naive_rag`.

Baseline node: `b2cd6b3c-observation-aligned`
Dataset: `local_comparison_v3.jsonl`
Profile: `benchmark_local_smoke_profile`
Scope: local smoke only; no full Hermes path, no remote/direct baseline, no behavior-layer changes.

## Run Integrity

| Baseline | total_cases | schema_valid_rate | completed_rate | run_error_count | failsoft_ok_rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `vanilla` | 90 | 1.0 | 1.0 | 0 | 1.0 |
| `finguard` | 90 | 1.0 | 1.0 | 0 | 1.0 |
| `naive_rag` | 90 | 1.0 | 1.0 | 0 | 1.0 |

All three baselines completed the same 90-case local-smoke dataset and wrote complete `rows.jsonl` / `summary.json` outputs.

## Fixed Three-Way Metrics

| Baseline | metadata_refusal_accuracy | raw_visible_refusal_accuracy | raw_behavior_safe_rate | aligned_visible_refusal_accuracy | aligned_behavior_safe_rate | over_refusal_rate | metadata_aligned_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vanilla` | 0.8111 | 0.9333 | 0.9333 | 0.9333 | 0.9333 | 0.0192 | 0.0 |
| `finguard` | 0.8556 | 0.9889 | 0.9889 | 0.9889 | 0.9889 | 0.0 | 0.8111 |
| `naive_rag` | 0.7667 | 0.8222 | 0.8222 | 0.8556 | 0.8556 | 0.0385 | 0.0 |

Interpretation:

FinGuard remains strongest on all three refusal/safety views: metadata refusal, raw visible behavior, and aligned visible behavior. Naive RAG runs cleanly at the same sample scale, but it trails both FinGuard and vanilla on visible behavior and has the highest over-refusal rate. The raw-to-aligned gain for `naive_rag` is an observation wording effect, not a model or retrieval behavior change.

## Category Readout

Aligned behavior-safe rate by category:

| Baseline | factual | compliance_sensitive | temporal | injection |
| --- | ---: | ---: | ---: | ---: |
| `vanilla` | 1.0 | 0.9706 | 0.9688 | 0.7273 |
| `finguard` | 1.0 | 1.0 | 1.0 | 0.9091 |
| `naive_rag` | 1.0 | 0.9412 | 0.9375 | 0.4545 |

Compliance over-refusal:

| Baseline | compliance_sensitive aligned_visible_over_refusal_rate |
| --- | ---: |
| `vanilla` | 0.0556 |
| `finguard` | 0.0 |
| `naive_rag` | 0.1111 |

## Result Boundary

This comparison establishes that `naive_rag` is now runnable at the same local-smoke sample scale as `vanilla` and `finguard`, but it does not improve the safety baseline. The main observed gap is injection handling: `naive_rag` reaches only `0.4545` aligned behavior-safe rate on injection cases versus `0.9091` for FinGuard.

Do not treat this as a full Hermes agent result. The next decision should be whether to analyze naive RAG failures at this local-smoke scale or expand the three-way comparison further; do not change prompt/corpus/behavior and expand in the same step.
