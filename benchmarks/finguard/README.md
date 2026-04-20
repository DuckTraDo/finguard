# FinGuard Benchmark Smoke

This directory holds the smallest end-to-end benchmark slice for FinGuard.

The goal is not to publish scores yet. The goal is to verify that:

- the dataset loads cleanly
- the run output stays on a stable schema
- summary metrics are computed consistently
- the current run stays aligned with the frozen engineering baseline

## Dataset

`smoke_dataset.jsonl` contains a compact set of representative finance prompts:

- factual
- compliance-sensitive refusal
- compliance-sensitive educational answer
- operational refusal
- prompt injection refusal
- temporal factual

`local_comparison_dataset.jsonl` is the original small-batch local profile set. It keeps the same schema and has 25 cases for early `vanilla` vs `finguard` comparison before larger benchmarks.

The current layered local comparison sets are:

- `local_comparison_v1.jsonl`: frozen 25-case comparison baseline.
- `local_comparison_v2_increment.jsonl`: 35 new stratified cases only.
- `local_comparison_v2.jsonl`: combined 60-case set used for the next local smoke comparison.

The v2 increment is stratified instead of random. It expands:

- factual and temporal factual finance questions
- numeric factual questions for traceability checks
- compliance-sensitive refusal cases
- compliance-sensitive educational cases that should include a disclaimer
- operational finance requests
- prompt-injection edge cases

Each row stores only the stable expected fields used for smoke validation:

- `query_type`
- `expected_behavior`
- `requires_explicit_dates`
- `refusal_expected`

## Runner Profiles

FinGuard has two benchmark execution profiles with different purposes:

- `benchmark_local_smoke_profile`: local, stable, repeatable smoke baseline. It uses localhost routing, a short benchmark-only prompt, no tools, no continuation loop, `think=false`, and a small output cap. Use this first to validate data loading, schema stability, local routing, and basic baseline comparability.
- `default`: full Hermes agent path. It keeps the normal Hermes system prompt, tools, and continuation behavior. Use this for real agent benchmark runs after the local smoke profile is green.

Do not compare scores from these two profiles as if they measure the same capability. The local smoke profile is a harness stability baseline; the default profile is the realistic agent benchmark.

## Runner

Run the smoke suite with:

```powershell
python -m finguard.benchmark_smoke `
  --dataset-path benchmarks/finguard/smoke_dataset.jsonl `
  --output-dir data/finguard_benchmark_smoke/manual_smoke `
  --baseline-tag finguard-classifier-verify-v2-green `
  --baseline-mode finguard `
  --limit 3
```

For local localhost smoke runs, use the benchmark-only local profile first:

```powershell
python -m finguard.benchmark_smoke `
  --dataset-path benchmarks/finguard/smoke_dataset.jsonl `
  --output-dir data/finguard_benchmark_smoke/local_profile_smoke `
  --baseline-tag finguard-classifier-verify-v2-green `
  --baseline-mode finguard `
  --run-profile benchmark_local_smoke_profile `
  --limit 3 `
  --max-tokens 192
```

After the 6-row smoke set is green, run the layered local comparison set with the same profile and compare only `vanilla` vs `finguard`:

```powershell
python -m finguard.benchmark_smoke `
  --dataset-path benchmarks/finguard/local_comparison_v2.jsonl `
  --output-dir data/finguard_benchmark_smoke/local_profile_comparison_v2/finguard `
  --baseline-tag finguard-local-smoke-profile-green `
  --dataset-name finguard_local_comparison_v2 `
  --baseline-mode finguard `
  --run-profile benchmark_local_smoke_profile `
  --max-tokens 192
```

`benchmark_local_smoke_profile` is intentionally narrow. It uses the same row and summary schema, but for `vanilla` and `finguard` local runs it uses a short benchmark prompt, disables tools, sends `think=false`, and performs one local chat-completions call with no continuation loop. This profile is the default local smoke baseline. It is for stable local smoke validation, not for measuring full Hermes agent capability.

After local smoke is green, run the full Hermes path explicitly by omitting `--run-profile benchmark_local_smoke_profile`:

```powershell
python -m finguard.benchmark_smoke `
  --dataset-path benchmarks/finguard/smoke_dataset.jsonl `
  --output-dir data/finguard_benchmark_smoke/full_hermes_smoke `
  --baseline-tag finguard-classifier-verify-v2-green `
  --baseline-mode finguard `
  --limit 3 `
  --max-tokens 192
```

Supported baseline modes:

- `direct`: bare model call with no Hermes loop and no FinGuard wrappers
- `vanilla`: Hermes loop with FinGuard guard/verify disabled
- `finguard`: Hermes loop with the frozen FinGuard baseline enabled

Default system labels and routing:

- `direct` -> `direct_remote`
- `vanilla` -> `hermes_vanilla_gemma`
- `finguard` -> `finguard_gemma`

For live smoke runs, `vanilla` and `finguard` now default to local routing:

- Gemma: `http://localhost:18080/v1`
- Qwen 3.5 / Qwen 3.6 / MiniMax profiles: `http://localhost:18081/v1`

If the selected local endpoint serves exactly one model, the runner auto-resolves that model id. You can override the routing explicitly with:

- `--system-label`
- `--model`
- `--provider`
- `--base-url`
- `--api-key`

Outputs:

- `rows.jsonl`: row-level results with expected vs actual comparisons
- `summary.json`: aggregate schema and alignment metrics
- `local_comparison_v2_benchmark_note.md`: formal result note for the first 60-case local comparison node
- `local_comparison_v2_results_draft.md`: Results/Method writing draft derived from the formal result note
- `local_comparison_v2_spot_check.md`: manual readout for the first 60-case local comparison pass
- `local_comparison_v2_failure_analysis.md`: failure analysis for the two FinGuard v2 mismatches

The local comparison summary fixes these interpretation metrics before larger benchmark expansion:

- `refusal_accuracy`: whether observed refusal matches the expected refusal label.
- `over_refusal_rate`: share of non-refusal-expected cases that still refused.
- `verification_downgraded_rate`: share of cases where FinVerify conservatively downgraded due to insufficient support.
- `category_breakdown`: expected-label decomposition for `factual`, `compliance_sensitive`, `injection`, and the cross-cutting `temporal` slice.

`category_breakdown.temporal` is intentionally overlapping: it includes every case where `requires_explicit_dates=true`, regardless of query type. Use it to inspect temporal behavior separately from the primary taxonomy.

Each row also records routing metadata so local vs remote execution is auditable:

- `provider_mode`
- `requested_provider`
- `requested_model`
- `resolved_model`
- `resolved_endpoint`
- `adapter_name`
- `provider_error_type`

## Recommended First Pass

Start with a very small live run, for example `--limit 3`, and verify:

- `schema_valid_rate == 1.0`
- `summary.json` has the same shape across `direct`, `vanilla`, and `finguard`
- `provider_mode == local` for `vanilla` and `finguard`
- `resolved_endpoint` points at the intended localhost adapter
- `baseline_alignment_rate` looks reasonable for the chosen model/config
- `failsoft_ok_rate == 1.0`
- `query_type_counts` and `verification_status_counts` are populated

After that, expand to the full smoke dataset, then move on to the larger benchmark set.
