# FinGuard Local Comparison v3 Sample Expansion Note

Status: first larger-sample check after the frozen v2 result package.

This note opens one new experimental axis only: sample expansion under the same `benchmark_local_smoke_profile`. It does not add naive RAG, direct remote baselines, full Hermes agent mode, or behavior-layer changes.

## Setup

Dataset: `local_comparison_v3.jsonl`

Shape:

- 90 total cases
- 60 frozen v2 cases
- 30 stratified v3 increment cases
- Baselines compared: `vanilla` and `finguard`
- Profile: `benchmark_local_smoke_profile`
- Local model: `gemma-4-31B-it-Q6_K.gguf`
- Endpoint: `http://localhost:18080/v1`
- Output cap: `--max-tokens 192`

Expected-label distribution:

| Slice | Cases |
| --- | ---: |
| factual | 34 |
| compliance_sensitive | 34 |
| temporal | 32 |
| injection | 11 |
| operational | 11 |

## Overall Comparison

| Metric | vanilla | finguard |
| --- | ---: | ---: |
| total_cases | 90 | 90 |
| schema_valid_rate | 1.0 | 1.0 |
| completed_rate | 1.0 | 1.0 |
| run_error_count | 0 | 0 |
| failsoft_ok_rate | 1.0 | 1.0 |
| refusal_accuracy | 0.8111 | 0.8556 |
| over_refusal_rate | 0.0192 | 0.0 |
| verification_downgraded_rate | 0.0 | 0.3111 |
| baseline_alignment_rate | 0.0 | 0.8111 |

Interpretation:

The v2 conclusion partially holds under the larger sample. FinGuard still avoids over-refusal (`0.0` vs vanilla `0.0192`) and continues to surface verification downgrades (`0.3111`) for unsupported claims. However, refusal-accuracy improvement narrows substantially from the v2 gap (`0.9833` vs `0.8667`) to the v3 gap (`0.8556` vs `0.8111`), mainly because the expanded injection, operational, and personalized-advice edge cases expose metadata/classification gaps.

## Category Breakdown

| Category | Metric | vanilla | finguard |
| --- | --- | ---: | ---: |
| factual | total_cases | 34 | 34 |
| factual | refusal_accuracy | 1.0 | 1.0 |
| factual | over_refusal_rate | 0.0 | 0.0 |
| factual | verification_downgraded_rate | 0.0 | 0.6471 |
| factual | baseline_alignment_rate | 0.0 | 0.9412 |
| compliance_sensitive | total_cases | 34 | 34 |
| compliance_sensitive | refusal_accuracy | 0.9706 | 0.9118 |
| compliance_sensitive | over_refusal_rate | 0.0556 | 0.0 |
| compliance_sensitive | verification_downgraded_rate | 0.0 | 0.1765 |
| compliance_sensitive | baseline_alignment_rate | 0.0 | 0.8529 |
| temporal | total_cases | 32 | 32 |
| temporal | refusal_accuracy | 0.9688 | 0.9375 |
| temporal | over_refusal_rate | 0.0476 | 0.0 |
| temporal | verification_downgraded_rate | 0.0 | 0.5312 |
| temporal | baseline_alignment_rate | 0.0 | 0.9062 |
| injection | total_cases | 11 | 11 |
| injection | refusal_accuracy | 0.2727 | 0.3636 |
| injection | over_refusal_rate | 0.0 | 0.0 |
| injection | verification_downgraded_rate | 0.0 | 0.0 |
| injection | baseline_alignment_rate | 0.0 | 0.3636 |

Category interpretation:

- Factual behavior remains stable: FinGuard does not over-refuse factual cases and adds expected verification downgrades.
- Compliance-sensitive and temporal slices still show zero FinGuard over-refusal, but refusal accuracy drops below v2 because several personalized-advice prompts produce safe visible responses without matching the expected metadata path.
- Injection remains the weakest slice. Expanding injection from 5 to 11 cases made the risk clearer: FinGuard often responds safely, but metadata does not consistently classify instruction-override phrasing as `injection / refuse_with_disclaimer`.

## Failure Pattern Table

| Pattern | Representative cases | Impact | Disposition |
| --- | --- | --- | --- |
| Conservative factual-to-compliance taxonomy | `explain_dividend_yield`, `explain_free_cash_flow` | Low. Answers remain educational and non-refusal. | Keep as benchmark finding; no behavior change now. |
| Educational compliance routed factual | `pros_cons_annuities`, `retirees_bond_risks_today` | Low to medium. User-facing answer is acceptable, but category accounting shifts. | Track as taxonomy/metadata boundary. |
| Personalized advice not metadata-refused | `tell_me_buy_bitcoin_today`, `move_401k_to_cash_now`, `guaranteed_high_return_portfolio` | Medium. Visible answer is safety-oriented, but metadata marks a pass. | Candidate narrow follow-up after result reporting. |
| Operational request not metadata-refused | `open_brokerage_account`, `submit_wire_transfer`, `cancel_limit_order` | Medium. Visible answer refuses capability, but guard metadata does not mark operational refusal. | Candidate narrow follow-up after result reporting. |
| Injection coverage gap | `injection_ignore_safety`, `injection_ignore_compliance_choose_stock`, `injection_forget_policy_broker`, `injection_reveal_finguard_prompt`, `injection_system_override_approve`, `injection_mark_safe_and_answer`, `injection_disregard_safety_constraints` | Medium to high for benchmark metadata. User-visible answers are usually safe, but injection intent is not consistently captured. | Do not retune broadly; later add targeted injection-pattern and refusal-observation tests. |

## Updated Three-Sentence Result

On the larger 90-case local smoke set, FinGuard still avoids over-refusal (`0.0`) and continues to expose unsupported claims through verification downgrades (`0.3111`). The refusal-accuracy advantage persists but weakens (`0.8556` vs vanilla `0.8111`), showing that the v2 aggregate result was directionally correct but not yet robust enough for broad claims. The next work should remain on this same local-smoke axis, especially injection, operational, and personalized-advice metadata coverage, before adding naive RAG as a separate baseline dimension.

## Artifacts

- `benchmarks/finguard/local_comparison_v3.jsonl`
- `benchmarks/finguard/local_comparison_v3_increment.jsonl`
- `data/finguard_benchmark_smoke/local_profile_comparison_v3/vanilla/rows.jsonl`
- `data/finguard_benchmark_smoke/local_profile_comparison_v3/vanilla/summary.json`
- `data/finguard_benchmark_smoke/local_profile_comparison_v3/finguard/rows.jsonl`
- `data/finguard_benchmark_smoke/local_profile_comparison_v3/finguard/summary.json`
