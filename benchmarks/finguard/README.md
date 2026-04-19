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

## Runner

Run the smoke suite with:

```powershell
python -m finguard.benchmark_smoke `
  --dataset-path benchmarks/finguard/smoke_dataset.jsonl `
  --output-dir data/finguard_benchmark_smoke/manual_smoke `
  --baseline-tag finguard-classifier-verify-v2-green `
  --limit 3
```

Outputs:

- `rows.jsonl`: row-level results with expected vs actual comparisons
- `summary.json`: aggregate schema and alignment metrics

## Recommended First Pass

Start with a very small live run, for example `--limit 3`, and verify:

- `schema_valid_rate == 1.0`
- `baseline_alignment_rate` looks reasonable for the chosen model/config
- `query_type_counts` and `verification_status_counts` are populated

After that, expand to the full smoke dataset, then move on to the larger benchmark set.
