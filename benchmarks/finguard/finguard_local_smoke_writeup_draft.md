# FinGuard Local Smoke Benchmark Writeup Draft

Status: publication-oriented writing skeleton. This document consolidates existing benchmark assets only; it does not add experiments, change behavior, or change benchmark code.

Baseline node: `b2cd6b3c-observation-aligned`
Primary dataset: `local_comparison_v3.jsonl`
Primary profile: `benchmark_local_smoke_profile`
Primary comparison: `vanilla` vs `finguard` vs `naive_rag`

## Abstract

Financial assistants need to answer educational questions while refusing personalized advice, account operations, and prompt-injection attempts. We present FinGuard, a lightweight guard/verify wrapper for a Hermes-style financial assistant, and evaluate it under a controlled local smoke profile designed to isolate safety routing, refusal behavior, and benchmark observability from full agent tool use. On a 90-case stratified local benchmark evaluated on Gemma 31B, FinGuard achieves the strongest aligned visible behavior safety (`0.989`) compared with vanilla local generation (`0.933`) and a static naive RAG baseline (`0.856`), while also reducing measured over-refusal to zero. We then repeat the vanilla-vs-FinGuard comparison on a Qwen3.5-27B local endpoint and observe the same pattern: FinGuard improves aligned behavior safety from `0.922` to `1.000` and reduces over-refusal from `0.154` to `0.000`. These results suggest the gains come from the wrapper architecture rather than single-model prompt tuning, while leaving full Hermes-agent, retrieval-heavy, and broader production evaluations for future work.

## Contributions

- We introduce a two-layer FinGuard wrapper that separates pre-generation guard routing from post-generation verification and conservative downgrade behavior.
- We define a local smoke benchmark profile that disables tools, continuation, and remote routing to produce reproducible local comparisons.
- We add structured benchmark fields that distinguish metadata refusal, raw visible refusal, aligned visible refusal, behavior safety, over-refusal, and metadata alignment.
- We evaluate `vanilla`, `finguard`, and `naive_rag` on the same 90-case stratified finance benchmark and report fixed comparison metrics.
- We demonstrate that FinGuard's local-smoke advantage transfers from Gemma 31B to Qwen3.5-27B without model-specific tuning, supporting the interpretation that the benefit comes from the wrapper architecture rather than single-model prompt engineering.
- We provide A/B failure typing that separates true visible behavior errors from safe-answer metadata, taxonomy, or observation mismatches.

## Introduction

Financial assistant safety is not only a refusal problem. A useful assistant must answer ordinary educational questions, handle temporal and numeric claims carefully, refuse personalized investment recommendations, decline account operations, and resist prompt-injection attempts. Systems that simply refuse broadly can look safe while being unhelpful; systems that answer broadly can look helpful while violating compliance-sensitive boundaries.

FinGuard addresses this tension by adding a minimal wrapper around an existing Hermes-style assistant instead of replacing the assistant with a new RAG stack or a fine-tuned model. The wrapper has two responsibilities: classify and route user queries before generation, then verify or downgrade unsupported claims after generation. The benchmark work in this package focuses on whether that wrapper improves local safety behavior and observability under controlled conditions.

The central question is:

> Under a reproducible local smoke profile, does FinGuard improve financial safety behavior and diagnostic observability compared with vanilla generation and static naive RAG?

The current answer is yes, with clear scope boundaries. FinGuard improves visible behavior safety, eliminates measured over-refusal in the 90-case run, and provides structured metadata for diagnosis. The same vanilla-vs-FinGuard pattern also appears on a Qwen3.5-27B local endpoint, suggesting the gain is not tied to a single local model. However, this result is not a claim about full Hermes agent performance, external retrieval quality, EDGAR grounding, or broad production generalization.

## Related Work

Financial-domain benchmarks have increasingly exposed the gap between general language-model fluency and reliable financial reasoning. FinanceBench (Islam et al., 2023) evaluates open-book financial question answering over public-company materials, emphasizing evidence-grounded answers to realistic analyst-style questions. CFinBench broadens this line in the Chinese financial setting, covering financial subjects, qualifications, practice, and law. These benchmarks are important for measuring domain knowledge and factual QA, but they primarily ask whether a model can produce the right answer. FinGuard instead asks whether a financial assistant routes, refuses, answers with disclaimers, or downgrades claims appropriately when questions cross compliance, temporal, operational, or prompt-injection boundaries.

Selective refusal and safety benchmarks study a complementary failure mode. RefusalBench examines when grounded language models should decline to answer because the supplied context is flawed or insufficient, showing that refusal behavior is not simply a matter of model scale or generic helpfulness. TRIDENT and Trident-Bench-style evaluations emphasize broader safety coverage, including harmful or professionally unsafe requests in high-stakes domains such as finance, law, and medicine. FinGuard builds on this concern with refusal correctness, but it separates three observable layers: structured metadata refusal, raw visible refusal, and observer-aligned visible refusal. This separation matters in finance because an answer can be behaviorally safe while still being misclassified by metadata or by a brittle observer.

LLM guardrail systems provide the closest architectural precedent. NeMo Guardrails represents guardrails as programmable rails that can sit around an LLM application, while Llama Guard frames safety as input and output classification over a risk taxonomy. Constitutional AI similarly shows how explicit normative principles can shape model behavior, though primarily through training and preference-style alignment rather than a lightweight runtime wrapper. These systems show the value of external or explicit policy enforcement, but FinGuard is narrower: it is not a general safety classifier, a fine-tuning recipe, or a replacement RAG system. It specializes wrapper logic for financial document QA, refusal correctness, temporal awareness, source normalization, and numeric traceability.

Finally, agent safety wrappers extend guardrails from single-turn moderation to runtime orchestration. Agentic systems must decide not only what text to generate, but also whether to call tools, trust retrieved context, expose hidden instructions, or execute user-requested account actions. Lightweight guardrail work is especially relevant here because production agents often need auditable policy checks without retraining the base model or replacing the surrounding application. FinGuard's local smoke profile deliberately disables full tool use to isolate the wrapper's behavior, but the design is motivated by this broader agent-safety setting: make the safety layer observable, fail-soft, and model-agnostic before evaluating richer full-agent behavior.

## Method

### Benchmark Profile

All primary results use `benchmark_local_smoke_profile`. This profile is intentionally narrow: it routes to a local Gemma model through `http://localhost:18080/v1`, uses a short benchmark-only prompt, disables tools, disables continuation, sends `think=false`, and caps generation with `--max-tokens 192`.

This profile is designed to measure benchmark plumbing, refusal behavior, over-refusal, visible safety, and wrapper metadata under reproducible local conditions. It should not be interpreted as the full Hermes agent path.

### Dataset

The primary dataset is `local_comparison_v3.jsonl`, a 90-case stratified local benchmark. It extends earlier v1/v2 local comparisons and includes:

- factual finance questions
- temporal factual questions requiring date awareness
- compliance-sensitive refusal cases
- compliance-sensitive educational cases that should be answered with disclaimer framing
- operational account/trade-action requests
- prompt-injection edge cases

Each case stores stable expected labels:

- `query_type`
- `expected_behavior`
- `requires_explicit_dates`
- `refusal_expected`

### Baselines

We compare three local-smoke baselines:

- `vanilla`: local model generation without FinGuard guard/verify wrappers.
- `finguard`: local model generation with the FinGuard guard and verify layers enabled.
- `naive_rag`: local model generation with static retrieval snippets added to the prompt, but without FinGuard wrappers or full agent tools.

The naive RAG baseline is intentionally minimal. It tests whether static context injection alone improves local smoke behavior; it is not a production retrieval system and does not replace full Hermes-agent benchmarking.

### Cross-Model Setup

The primary three-way comparison uses the local Gemma endpoint. To test whether FinGuard's advantage transfers across model families, we also run the same 90-case `local_comparison_v3.jsonl` benchmark on a Qwen3.5-27B local endpoint exposed at `http://localhost:18080/v1`.

The same local endpoint address (`http://localhost:18080/v1`) was reused across experimental phases; the underlying model was swapped between Gemma 31B and Qwen3.5-27B between runs, with only one model served at any given time.

The Qwen migration check compares only:

- `vanilla_qwen`: Qwen local generation without FinGuard guard/verify wrappers.
- `finguard_qwen`: Qwen local generation with FinGuard guard and verify enabled.

We do not run `naive_rag_qwen` in the mainline result. That would introduce a second experimental axis and is left as a possible appendix or follow-up.

### Metrics

The benchmark reports both legacy metadata-oriented and observation-aligned behavior metrics:

- `metadata_refusal_accuracy`: whether the metadata/refusal path matches the expected refusal label.
- `raw_visible_refusal_accuracy`: visible refusal accuracy before observer-only wording alignment.
- `aligned_visible_refusal_accuracy`: visible refusal accuracy after benchmark-only wording alignment.
- `raw_behavior_safe_rate`: visible behavior safety before wording alignment.
- `aligned_behavior_safe_rate`: visible behavior safety after wording alignment.
- `over_refusal_rate`: rate of refusing when the expected behavior was non-refusal.
- `metadata_aligned_rate`: whether structured metadata matches the expected benchmark path.

This separation is important: observation alignment can correct benchmark wording coverage without changing model behavior.

## Results

### Overview Result Table

| Baseline | total_cases | schema_valid_rate | completed_rate | metadata_refusal_accuracy | raw_visible_refusal_accuracy | aligned_visible_refusal_accuracy | aligned_behavior_safe_rate | over_refusal_rate | metadata_aligned_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `vanilla` | 90 | 1.000 | 1.000 | 0.811 | 0.933 | 0.933 | 0.933 | 0.019 | 0.000 |
| `finguard` | 90 | 1.000 | 1.000 | 0.856 | 0.989 | 0.989 | 0.989 | 0.000 | 0.811 |
| `naive_rag` | 90 | 1.000 | 1.000 | 0.767 | 0.822 | 0.856 | 0.856 | 0.039 | 0.000 |

FinGuard is strongest across all primary safety views. It has the highest metadata refusal accuracy, raw visible refusal accuracy, aligned visible refusal accuracy, and aligned behavior-safe rate. It is also the only baseline with zero measured over-refusal and nonzero metadata alignment.

### Category Breakdown

Aligned behavior-safe rate by category:

| Baseline | factual | compliance_sensitive | temporal | injection |
| --- | ---: | ---: | ---: | ---: |
| `vanilla` | 1.000 | 0.971 | 0.969 | 0.727 |
| `finguard` | 1.000 | 1.000 | 1.000 | 0.909 |
| `naive_rag` | 1.000 | 0.941 | 0.938 | 0.455 |

FinGuard matches or exceeds the other baselines in every category. Injection remains the hardest slice for all systems, but FinGuard remains substantially stronger than both vanilla and naive RAG.

### Cross-Model Generalization

We next test whether the FinGuard advantage transfers from the initial Gemma local endpoint to Qwen3.5-27B under the same local smoke profile. The goal is not to claim broad multi-model generalization, but to check whether the wrapper's benefit survives a model-family change without changing the classifier, guard, verify, or benchmark profile.

| Model | Baseline | metadata_refusal_accuracy | raw_visible_refusal_accuracy | aligned_visible_refusal_accuracy | aligned_behavior_safe_rate | over_refusal_rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Gemma 31B | `vanilla` | 0.811 | 0.933 | 0.933 | 0.933 | 0.019 |
| Gemma 31B | `finguard` | 0.856 | 0.989 | 0.989 | 0.989 | 0.000 |
| Qwen3.5-27B | `vanilla_qwen` | 0.778 | 0.878 | 0.922 | 0.922 | 0.154 |
| Qwen3.5-27B | `finguard_qwen` | 0.856 | 0.944 | 1.000 | 1.000 | 0.000 |

The cross-model pattern is consistent. On both Gemma 31B and Qwen, FinGuard improves metadata refusal accuracy, raw visible refusal accuracy, aligned visible refusal accuracy, aligned behavior safety, and over-refusal. The Qwen result is especially clear on aligned behavior safety: `finguard_qwen` reaches `1.000` versus `0.922` for `vanilla_qwen`, while the raw-to-aligned difference shows the effect of observer-only wording alignment.

Cross-model conclusion:

> FinGuard's local-smoke advantage transfers from Gemma to Qwen3.5-27B without model-specific prompt or behavior tuning. The improvement is therefore best attributed to the wrapper architecture: explicit guard routing, verification-aware post-processing, and structured benchmark metadata, rather than to a single model's idiosyncratic refusal style.

### Failure Typing

FinGuard v3 mismatch typing found 17 typed mismatches: 1 Class A real behavior error and 16 Class B metadata, taxonomy, coverage, or observation mismatches. Naive RAG failure typing found 16 typed records: 2 Class A real behavior problems and 14 Class B observation/metadata mismatches.

| Boundary | FinGuard total typed | FinGuard A | FinGuard B | Naive RAG total typed | Naive RAG A | Naive RAG B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| injection | 7 | 1 | 6 | 8 | 0 | 8 |
| operational | 3 | 0 | 3 | 5 | 0 | 5 |
| personalized / educational | 7 | 0 | 7 | 3 | 2 | 1 |
| other | 0 | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 1 | 16 | 16 | 2 | 14 |

This table should be interpreted carefully. Neither system collapses into unsafe financial advice in this run. FinGuard's residual issues are mostly structured metadata or taxonomy alignment problems, while naive RAG's residual issues are mostly observation coverage plus two conservative over-refusals on educational finance prompts.

## Discussion

Observation alignment does not eliminate FinGuard's advantage. After raw/aligned refusal views are separated, FinGuard still leads naive RAG on aligned behavior-safe rate (`0.989` vs `0.856`), aligned visible refusal accuracy (`0.989` vs `0.856`), metadata refusal accuracy (`0.856` vs `0.767`), and over-refusal (`0.000` vs `0.039`).

The cross-model result strengthens this interpretation. Qwen changes the base model behavior substantially: vanilla Qwen has lower metadata refusal accuracy (`0.778`) and higher over-refusal (`0.154`) than vanilla Gemma. FinGuard still restores the same structured pattern: metadata refusal accuracy rises to `0.856`, aligned behavior safety reaches `1.000`, and over-refusal drops to `0.000`. This makes the result less likely to be an artifact of Gemma-specific wording and more likely to come from the wrapper architecture.

The reason is structural. FinGuard records query type, expected behavior, temporal intent, verification downgrade, and metadata alignment. Even when the visible answer is safe but the metadata route is imperfect, the benchmark can diagnose the failure mode. Naive RAG appends static context, but it has no comparable policy or verification layer. Its safe refusals are therefore harder to measure unless the observer catches the exact wording.

The injection slice illustrates the difference. Manual typing shows that naive RAG often refuses injection-like requests, but the observer misses many safe refusal phrasings such as refusing to reveal hidden prompts, disable safety systems, or ignore safety rules. FinGuard also has injection metadata misses, but its aligned behavior-safe rate on injection is much higher (`0.909` vs `0.455`), and its structured wrapper makes the intended refusal path more recoverable.

The usefulness tradeoff is also different. Naive RAG has two Class A failures caused by conservative over-refusal on educational finance questions where a disclaimered answer was expected. FinGuard's comparable personalized/educational failures are Class B taxonomy or metadata issues: visible answers remain safe or educational, but structured labels do not always match the benchmark framing.

## Limitations

This result is intentionally scoped. It should not be presented as a complete evaluation of Hermes, all financial agent behavior, or all retrieval-augmented systems.

- The benchmark uses `benchmark_local_smoke_profile`, not the full Hermes agent path with tools and continuation.
- The primary dataset has 90 cases, which is enough for local smoke comparison but not a large-scale benchmark.
- The naive RAG baseline uses static local snippets, not a production-grade retriever.
- The Qwen result covers `vanilla_qwen` and `finguard_qwen` only; it does not include `naive_rag_qwen`.
- Observation alignment improves measurement coverage but remains a benchmark heuristic.
- Metadata-aligned metrics are asymmetric: FinGuard emits structured guard/verify metadata, while vanilla and naive RAG do not.
- The benchmark emphasizes refusal, over-refusal, injection, operational, temporal, and traceability behavior; it does not yet measure full factual accuracy against external authoritative sources.

## Current Claim Boundary

A safe publication claim is:

> Under a controlled local smoke profile, FinGuard improves visible safety behavior, reduces over-refusal, and provides structured observability compared with vanilla local generation and a static naive RAG baseline on Gemma 31B. The vanilla-vs-FinGuard advantage also transfers from Gemma 31B to Qwen3.5-27B, suggesting the gain comes from the wrapper architecture rather than single-model-specific tuning.

Claims that should wait for future work:

- FinGuard outperforms all full agent systems.
- FinGuard solves factual grounding or live financial data retrieval.
- Naive RAG is generally unsafe.
- The result generalizes across all models, providers, or production traffic.
