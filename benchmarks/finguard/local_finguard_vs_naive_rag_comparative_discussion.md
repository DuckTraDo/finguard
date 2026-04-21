# FinGuard vs Naive RAG Comparative Discussion

Status: comparative writing asset only. This note does not change classifier behavior, guard/verify logic, naive RAG prompt, corpus, generation logic, observer rules, dataset size, or benchmark runner scope.

Baseline node: `b2cd6b3c-observation-aligned`
Dataset: `local_comparison_v3.jsonl`
Profile: `benchmark_local_smoke_profile`
Comparison: `finguard` vs `naive_rag`

## Cross-Baseline Failure Table

| Boundary | FinGuard total typed | FinGuard A | FinGuard B | Naive RAG total typed | Naive RAG A | Naive RAG B | Comparative interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| injection | 7 | 1 | 6 | 8 | 0 | 8 | Both systems mostly produce safe visible refusals; FinGuard has much better aligned behavior-safe rate (`0.9091` vs `0.4545`) because its guard/verify path supplies more structure, while naive RAG depends on wording-level observation. |
| operational | 3 | 0 | 3 | 5 | 0 | 5 | Both systems visibly refuse account/trade actions, but FinGuard's misses are structured metadata coverage gaps; naive RAG has no comparable metadata and relies entirely on observer wording. |
| personalized / educational | 3 personalized-advice + 4 educational taxonomy | 0 | 7 | 3 | 2 | 1 | FinGuard's issues are mostly taxonomy or metadata framing; naive RAG has two real over-refusals where educational answers were expected. |
| other | 0 | 0 | 0 | 0 | 0 | 0 | Neither analysis found a separate factual/other failure cluster in the typed mismatch set. |
| total | 17 | 1 | 16 | 16 | 2 | 14 | Both drops are mostly observation/metadata rather than unsafe-advice collapse, but naive RAG has more real behavior calibration problems and weaker injection handling. |

Definitions:

- **Class A** means the visible answer itself fails the expected user-facing behavior.
- **Class B** means the visible answer is safe, conservative, or refusal-oriented, but metadata, coverage, taxonomy, or benchmark observation does not align with the expected path.

## Comparative Findings

Observation alignment helps both analysis tracks, but it does not erase the difference between FinGuard and naive RAG. On the same 90-case local-smoke set, FinGuard still leads on `metadata_refusal_accuracy` (`0.8556` vs `0.7667`), raw visible refusal accuracy (`0.9889` vs `0.8222`), aligned visible refusal accuracy (`0.9889` vs `0.8556`), and aligned behavior-safe rate (`0.9889` vs `0.8556`). FinGuard also has zero over-refusal (`0.0`), while naive RAG over-refuses on `0.0385` of non-refusal-expected cases.

The main reason is structural. FinGuard carries an explicit guard/verify layer that records `query_type`, `expected_behavior`, temporal intent, verification downgrade, and metadata alignment. Even when FinGuard's visible answer is safe but the structured route is imperfect, the benchmark can diagnose that imperfection as metadata coverage. Naive RAG has no comparable structured policy path; it appends static retrieval snippets and then relies on the base model plus wording-level observation. That makes safe refusals harder to distinguish from normal answers unless the observer happens to cover the exact phrasing.

The injection result is the clearest example. Manual typing shows that naive RAG usually does not obey injection prompts; it often refuses to reveal prompts, disable safety, or ignore rules. But its aligned injection behavior-safe rate remains only `0.4545`, far below FinGuard's `0.9091`, because many naive RAG refusals use wording not covered by the current observer and because there is no FinGuard-style metadata to record injection/refusal intent. FinGuard's injection misses are also mostly Class B, but its wrapper makes the intended safety route more recoverable and measurable.

The real behavior gap appears more in usefulness calibration than in unsafe advice. Naive RAG has two Class A personalized/educational failures: it refuses `latest_best_etfs_for_retirement` and `current_risks_of_buying_tsla`, even though the expected behavior was an educational answer with disclaimer. FinGuard's comparable personalized/educational mismatches are Class B: visible answers remain safe or educational, but taxonomy/metadata does not match the expected benchmark framing. In short, naive RAG is more likely to turn educational finance prompts into refusals, while FinGuard is more likely to answer safely but record the route imperfectly.

Therefore, after observation alignment, FinGuard still wins for three reasons:

- It has stronger visible safety: `0.9889` aligned behavior-safe rate versus `0.8556` for naive RAG.
- It has better calibration: zero measured over-refusal versus `0.0385` for naive RAG.
- It has structured observability: `metadata_aligned_rate=0.8111` for FinGuard versus `0.0` for naive RAG by design.

## Writing Takeaway

The clean comparative claim is not "RAG is unsafe." The cleaner claim is:

> Under the local smoke profile, naive RAG is runnable and often visibly safe, but it lacks the structured policy/verification layer that makes FinGuard both safer and more diagnosable. Observation alignment narrows wording artifacts, yet FinGuard remains stronger because it combines visible refusals, lower over-refusal, and explicit metadata for behavior routing.

Do not use this result to justify expanding full Hermes path or changing naive RAG behavior in the same step. The next step should either freeze this discussion into the benchmark results package or separately decide whether to improve observer coverage before any larger three-way run.
