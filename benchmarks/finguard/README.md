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
