# FinGuard Local Comparison v3 Fixed Result Table

Status: fixed result asset for the observation-aligned benchmark node. Behavior-layer code remains frozen at `b2cd6b3c`.

Profile: `benchmark_local_smoke_profile`
Dataset: `local_comparison_v3.jsonl`
Comparison: `vanilla` vs `finguard`

| Metric | vanilla | finguard | Interpretation |
| --- | ---: | ---: | --- |
| `refusal_accuracy` | 0.8111 | 0.8556 | Legacy metadata/refusal-path headline metric. |
| `over_refusal_rate` | 0.0192 | 0.0 | FinGuard does not increase refusal on non-refusal-expected cases. |
| `behavior_safe_rate` | 0.9333 | 0.9889 | Visible answer behavior is safer after FinGuard observation alignment. |
| `metadata_aligned_rate` | 0.0 | 0.8111 | FinGuard emits structured guard/verify metadata; vanilla has no comparable FinGuard metadata path. |

Three-sentence conclusion:

FinGuard improves the local-smoke v3 headline refusal metric while reducing measured over-refusal to zero. The observation-aligned view shows the stronger result is visible answer behavior: 89 of 90 FinGuard answers match the expected refusal/non-refusal behavior. Metadata alignment remains the remaining engineering gap, especially for safe visible answers whose structured path is still recorded differently from the benchmark label.

Boundary note:

This table is a stable result package for the local smoke profile only. It should not be read as a full Hermes agent benchmark or as evidence about retrieval-augmented baselines. The next experiment axis is a small local-smoke `naive_rag` run using the same lightweight profile, not the full Hermes path.
