from finguard.config import FinGuardConfig
from finguard.fin_guard import FinGuardLayer


def _guard() -> FinGuardLayer:
    return FinGuardLayer(FinGuardConfig())


def test_temporal_direct_advice_stays_refusal():
    result = _guard().process("Should I buy this stock now?")

    assert result.passed is False
    assert result.query_type == "compliance_sensitive"
    assert result.expected_behavior == "refuse_with_disclaimer"
    assert result.temporal_intent["detected"] is True
    assert "relative_time" in result.temporal_intent["signals"]
    assert result.time_context["requires_explicit_dates"] is True


def test_temporal_educational_query_stays_answer_with_disclaimer():
    result = _guard().process("Explain the risks of buying this stock today.")

    assert result.passed is True
    assert result.query_type == "compliance_sensitive"
    assert result.expected_behavior == "answer_with_disclaimer"
    assert result.temporal_intent["detected"] is True
    assert "Use explicit dates" in result.augmented_query


def test_temporal_market_data_query_stays_factual():
    result = _guard().process("What is the latest default rate?")

    assert result.passed is True
    assert result.query_type == "factual"
    assert result.expected_behavior == "answer_normally"
    assert result.temporal_intent["detected"] is True
    assert result.time_context["requires_explicit_dates"] is True
