from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Callable

DEFAULT_BASELINE_TAG = "finguard-classifier-verify-v2-green"
DEFAULT_DATASET_PATH = Path(__file__).resolve().parent.parent / "benchmarks" / "finguard" / "smoke_dataset.jsonl"
DEFAULT_OUTPUT_ROOT = Path("data") / "finguard_benchmark_smoke"

REQUIRED_CASE_KEYS = {"id", "prompt", "expected"}
REQUIRED_EXPECTED_KEYS = {
    "query_type",
    "expected_behavior",
    "requires_explicit_dates",
    "refusal_expected",
}
REQUIRED_ROW_KEYS = {
    "id",
    "prompt",
    "expected",
    "actual",
    "matches",
    "baseline_match",
    "schema_errors",
}
REQUIRED_ACTUAL_KEYS = {
    "completed",
    "partial",
    "query_type",
    "expected_behavior",
    "requires_explicit_dates",
    "refusal_observed",
    "verification_status",
    "verification_downgraded",
    "source_count",
    "query_augmented",
    "classification_reasons",
    "final_response_preview",
}

AgentFactory = Callable[[], Any]


def load_smoke_dataset(dataset_path: str | Path = DEFAULT_DATASET_PATH) -> list[dict[str, Any]]:
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark smoke dataset not found: {path}")

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            missing = REQUIRED_CASE_KEYS - set(payload)
            if missing:
                raise ValueError(f"{path}:{line_number} missing keys: {sorted(missing)}")

            case_id = str(payload["id"])
            if case_id in seen_ids:
                raise ValueError(f"{path}:{line_number} duplicate case id: {case_id}")
            seen_ids.add(case_id)

            expected = payload["expected"]
            if not isinstance(expected, dict):
                raise ValueError(f"{path}:{line_number} expected must be an object")
            expected_missing = REQUIRED_EXPECTED_KEYS - set(expected)
            if expected_missing:
                raise ValueError(
                    f"{path}:{line_number} expected missing keys: {sorted(expected_missing)}"
                )

            rows.append(
                {
                    "id": case_id,
                    "prompt": str(payload["prompt"]),
                    "expected": {
                        "query_type": str(expected["query_type"]),
                        "expected_behavior": str(expected["expected_behavior"]),
                        "requires_explicit_dates": bool(expected["requires_explicit_dates"]),
                        "refusal_expected": bool(expected["refusal_expected"]),
                    },
                }
            )

    if not rows:
        raise ValueError(f"No benchmark smoke cases found in {path}")

    return rows


def create_default_agent_factory(
    *,
    model: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> AgentFactory:
    def factory():
        from run_agent import AIAgent

        resolved_base_url = (
            base_url
            or os.environ.get("OPENROUTER_BASE_URL")
            or os.environ.get("BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
        resolved_api_key = (
            api_key
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("CODEX_API_KEY")
            or ""
        )
        return AIAgent(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=model,
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            save_trajectories=False,
        )

    return factory


def build_benchmark_row(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    finguard = dict(result.get("finguard") or {})
    time_context = dict(finguard.get("time_context") or {})
    final_response = str(result.get("final_response") or "")
    actual = {
        "completed": bool(result.get("completed", False)),
        "partial": bool(result.get("partial", False)),
        "query_type": finguard.get("query_type"),
        "expected_behavior": finguard.get("expected_behavior"),
        "requires_explicit_dates": bool(time_context.get("requires_explicit_dates", False)),
        "refusal_observed": not bool(finguard.get("passed", True)),
        "verification_status": str(finguard.get("verification_status") or "not_applicable"),
        "verification_downgraded": bool(finguard.get("verification_downgraded", False)),
        "source_count": int(finguard.get("source_count", 0) or 0),
        "query_augmented": bool(finguard.get("query_augmented", False)),
        "classification_reasons": list(finguard.get("classification_reasons") or []),
        "final_response_preview": final_response[:240],
    }
    matches = {
        "query_type": actual["query_type"] == case["expected"]["query_type"],
        "expected_behavior": actual["expected_behavior"] == case["expected"]["expected_behavior"],
        "requires_explicit_dates": actual["requires_explicit_dates"]
        == case["expected"]["requires_explicit_dates"],
        "refusal_observed": actual["refusal_observed"] == case["expected"]["refusal_expected"],
    }
    row = {
        "id": case["id"],
        "prompt": case["prompt"],
        "expected": dict(case["expected"]),
        "actual": actual,
        "matches": matches,
        "baseline_match": all(matches.values()),
        "schema_errors": [],
    }
    row["schema_errors"] = validate_benchmark_row(row)
    return row


def validate_benchmark_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_row_keys = REQUIRED_ROW_KEYS - set(row)
    if missing_row_keys:
        errors.append(f"missing_row_keys:{','.join(sorted(missing_row_keys))}")

    actual = row.get("actual")
    if not isinstance(actual, dict):
        errors.append("actual_not_object")
    else:
        missing_actual_keys = REQUIRED_ACTUAL_KEYS - set(actual)
        if missing_actual_keys:
            errors.append(f"missing_actual_keys:{','.join(sorted(missing_actual_keys))}")

    matches = row.get("matches")
    if not isinstance(matches, dict):
        errors.append("matches_not_object")
    elif set(matches) != {
        "query_type",
        "expected_behavior",
        "requires_explicit_dates",
        "refusal_observed",
    }:
        errors.append("unexpected_match_keys")

    if not isinstance(row.get("baseline_match"), bool):
        errors.append("baseline_match_not_bool")

    return errors


def summarize_rows(
    rows: list[dict[str, Any]],
    *,
    baseline_tag: str = DEFAULT_BASELINE_TAG,
    dataset_name: str = "finguard_smoke",
) -> dict[str, Any]:
    total_cases = len(rows)
    if total_cases == 0:
        raise ValueError("Cannot summarize an empty benchmark smoke run")

    schema_valid_count = sum(1 for row in rows if not row["schema_errors"])
    completed_count = sum(1 for row in rows if row["actual"]["completed"])
    partial_count = sum(1 for row in rows if row["actual"]["partial"])
    query_type_match_count = sum(1 for row in rows if row["matches"]["query_type"])
    expected_behavior_match_count = sum(1 for row in rows if row["matches"]["expected_behavior"])
    temporal_match_count = sum(1 for row in rows if row["matches"]["requires_explicit_dates"])
    refusal_match_count = sum(1 for row in rows if row["matches"]["refusal_observed"])
    baseline_match_count = sum(1 for row in rows if row["baseline_match"])
    verification_downgraded_count = sum(
        1 for row in rows if row["actual"]["verification_downgraded"]
    )

    query_type_counts = Counter(str(row["actual"]["query_type"] or "unknown") for row in rows)
    verification_status_counts = Counter(
        str(row["actual"]["verification_status"] or "unknown") for row in rows
    )

    return {
        "dataset_name": dataset_name,
        "baseline_tag": baseline_tag,
        "total_cases": total_cases,
        "schema_valid_count": schema_valid_count,
        "schema_valid_rate": round(schema_valid_count / total_cases, 4),
        "completed_rate": round(completed_count / total_cases, 4),
        "partial_rate": round(partial_count / total_cases, 4),
        "query_type_accuracy": round(query_type_match_count / total_cases, 4),
        "expected_behavior_accuracy": round(expected_behavior_match_count / total_cases, 4),
        "temporal_accuracy": round(temporal_match_count / total_cases, 4),
        "refusal_accuracy": round(refusal_match_count / total_cases, 4),
        "baseline_alignment_rate": round(baseline_match_count / total_cases, 4),
        "verification_downgraded_rate": round(verification_downgraded_count / total_cases, 4),
        "query_type_counts": dict(sorted(query_type_counts.items())),
        "verification_status_counts": dict(sorted(verification_status_counts.items())),
    }


def write_smoke_outputs(
    *,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    output_dir: str | Path,
) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    rows_file = path / "rows.jsonl"
    summary_file = path / "summary.json"

    with rows_file.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    with summary_file.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)


def run_smoke_benchmark(
    *,
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_ROOT,
    baseline_tag: str = DEFAULT_BASELINE_TAG,
    dataset_name: str = "finguard_smoke",
    limit: int | None = None,
    agent_factory: AgentFactory | None = None,
    model: str = "anthropic/claude-sonnet-4.6",
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    cases = load_smoke_dataset(dataset_path)
    if limit is not None:
        cases = cases[:limit]

    if agent_factory is None:
        agent_factory = create_default_agent_factory(
            model=model,
            base_url=base_url,
            api_key=api_key,
        )

    rows: list[dict[str, Any]] = []
    for case in cases:
        agent = agent_factory()
        result = agent.run_conversation(case["prompt"])
        rows.append(build_benchmark_row(case, result))

    summary = summarize_rows(rows, baseline_tag=baseline_tag, dataset_name=dataset_name)
    write_smoke_outputs(rows=rows, summary=summary, output_dir=output_dir)
    return {"rows": rows, "summary": summary}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the FinGuard benchmark smoke suite.")
    parser.add_argument(
        "--dataset-path",
        default=str(DEFAULT_DATASET_PATH),
        help="JSONL dataset with prompt + expected benchmark fields.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory where rows.jsonl and summary.json will be written.",
    )
    parser.add_argument(
        "--baseline-tag",
        default=DEFAULT_BASELINE_TAG,
        help="Frozen engineering baseline tag used for alignment checks.",
    )
    parser.add_argument(
        "--dataset-name",
        default="finguard_smoke",
        help="Logical dataset name to store in the summary output.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of cases to run from the front of the dataset.",
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-sonnet-4.6",
        help="Model name to use for live smoke runs.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Optional API base URL override for live smoke runs.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional API key override for live smoke runs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    outcome = run_smoke_benchmark(
        dataset_path=args.dataset_path,
        output_dir=args.output_dir,
        baseline_tag=args.baseline_tag,
        dataset_name=args.dataset_name,
        limit=args.limit,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )
    print(json.dumps(outcome["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
