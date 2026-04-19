import json
from pathlib import Path

from finguard.config import FinGuardConfig
from finguard.fin_guard import FinGuardLayer


def test_guard_dev_regression_matrix():
    fixture_path = Path(__file__).parent / "fixtures" / "dev_regression_set.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    for case in cases:
        config = FinGuardConfig(
            strict_financial_scope=bool(case.get("strict_financial_scope", False))
        )
        result = FinGuardLayer(config).process(case["query"])
        expected = case["expected"]

        assert result.passed == expected["passed"], case["name"]
        assert result.query_type == expected["query_type"], case["name"]
        assert result.expected_behavior == expected["expected_behavior"], case["name"]
        assert result.finance_scope == expected["finance_scope"], case["name"]
        assert bool((result.time_context or {}).get("requires_explicit_dates")) == expected[
            "requires_explicit_dates"
        ], case["name"]
