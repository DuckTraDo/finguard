from finguard.config import FinGuardConfig
from finguard.fin_classifier import (
    REASON_DIRECT_ADVICE_PATTERN,
    REASON_GENERAL_RECOMMENDATION_PATTERN,
    REASON_OPERATIONAL_PATTERN,
    REASON_OPTIONAL_REFINER,
    REASON_TEMPORAL_INTENT,
    ClassificationResult,
    FinClassifier,
)


def _classifier(**config_overrides) -> FinClassifier:
    return FinClassifier(FinGuardConfig(**config_overrides))


def test_latest_default_rate_is_factual_and_temporal():
    result = _classifier().classify("What is the latest default rate?")

    assert result.query_type == "factual"
    assert result.expected_behavior == "answer_normally"
    assert result.finance_scope is True
    assert result.temporal_intent["detected"] is True
    assert "relative_time" in result.temporal_intent["signals"]
    assert REASON_TEMPORAL_INTENT in result.reasons


def test_general_recommendation_without_personalization_gets_disclaimer():
    result = _classifier().classify("What are the best dividend stocks right now?")

    assert result.query_type == "compliance_sensitive"
    assert result.expected_behavior == "answer_with_disclaimer"
    assert result.finance_scope is True
    assert result.temporal_intent["detected"] is True
    assert REASON_GENERAL_RECOMMENDATION_PATTERN in result.reasons


def test_operational_boundary_catches_transfer_request():
    result = _classifier().classify("Transfer funds from my savings account to my brokerage.")

    assert result.query_type == "operational"
    assert result.expected_behavior == "refuse_with_disclaimer"
    assert result.finance_scope is True
    assert REASON_OPERATIONAL_PATTERN in result.reasons


def test_optional_classifier_refiner_can_adjust_ambiguous_finance_query():
    def decision_refiner(query: str, base_result: ClassificationResult) -> ClassificationResult | None:
        assert query == "Thoughts on municipal bonds?"
        assert base_result.query_type == "factual"
        return ClassificationResult(
            query_type="compliance_sensitive",
            expected_behavior="answer_with_disclaimer",
            confidence=0.91,
            finance_scope=True,
            temporal_intent={
                "detected": False,
                "signals": [],
                "requires_explicit_dates": False,
                "relative_terms": [],
                "years": [],
                "quarters": [],
            },
            reasons=["context.market_commentary"],
        )

    classifier = FinClassifier(
        FinGuardConfig(
            enable_llm_classifier_refiner=True,
            classifier_refiner_confidence_floor=0.8,
        ),
        decision_refiner=decision_refiner,
    )

    result = classifier.classify("Thoughts on municipal bonds?")

    assert result.query_type == "compliance_sensitive"
    assert result.expected_behavior == "answer_with_disclaimer"
    assert result.llm_refined is True
    assert REASON_OPTIONAL_REFINER in result.reasons


def test_personalized_direct_advice_keeps_stable_reason_labels():
    result = _classifier().classify("Should I buy AAPL right now?")

    assert REASON_TEMPORAL_INTENT in result.reasons
    assert REASON_DIRECT_ADVICE_PATTERN in result.reasons
