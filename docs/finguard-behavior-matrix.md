# FinGuard Behavior Matrix

This table is the runtime contract for the FinGuard wrapper. It explains how
`query_type`, `expected_behavior`, and verify actions fit together so tests,
benchmarks, and future ablations all measure the same thing.

## Decision Table

| query_type | expected_behavior | Guard action | Verify action | Intended user-visible behavior |
| --- | --- | --- | --- | --- |
| `factual` | `answer_normally` | pass through | normalize sources, verify numeric claims, append citations when available | answer directly |
| `compliance_sensitive` | `refuse_with_disclaimer` | block before LLM loop | none | minimal refusal with disclaimer |
| `compliance_sensitive` | `answer_with_disclaimer` | pass through with conservative augmentation | normalize sources, verify numeric claims, append disclaimer and citations | educational answer plus disclaimer |
| `operational` | `refuse_with_disclaimer` | block before LLM loop | none | refuse trades, transfers, or execution |
| `injection` | `refuse_with_disclaimer` | block before LLM loop | none | refuse prompt override attempts |
| `out_of_scope` | `refuse_with_disclaimer` when strict scope is enabled | block before LLM loop | none | refuse non-finance requests in strict mode |

## Fail-Soft Rules

- Guard failure: continue with the raw user query and record `guard_status=failed`.
- Verify failure: return the raw Hermes answer and record `verify_status=failed`.
- Missing sources: keep the answer, return `sources=[]`, and mark numeric claims as unverified when needed.
- Missing or partial tool traces: `source_normalizer()` should salvage whatever can be normalized instead of throwing.

## Metrics To Track

- `guard_latency_ms`
- `verify_latency_ms`
- `source_count`
- `numeric_claim_count`
- `verified_number_count`
- `guard_status`
- `verify_status`

## Current Scope Notes

- `query_type` stays aligned with the original brief taxonomy.
- `expected_behavior` is the second-stage action label used to disambiguate compliance cases.
- The current classifier is rules-first. A future LLM-backed classifier should preserve this contract unless the matrix is updated deliberately.
