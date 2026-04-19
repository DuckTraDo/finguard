from finguard.config import FinGuardConfig
from finguard.fin_verify import FinVerifyLayer


def test_verify_unverified_numbers_without_sources_gets_cautious_prefix():
    verifier = FinVerifyLayer(FinGuardConfig())

    result = verifier.process(
        response="AAPL revenue was 100 in 2023.",
        sources=[],
        query_type="factual",
        expected_behavior="answer_normally",
        finance_scope=True,
    )

    assert result.verification_status == "unverified"
    assert result.downgraded_for_verification is True
    assert result.supported_numbers == []
    assert result.unverified_numbers == ["100", "2023"]
    assert result.final_response.startswith(
        "I could not verify the specific figures below because no captured sources were available."
    )
    assert "Verification note: no captured sources were available" in result.final_response


def test_verify_partially_verified_numbers_get_cautious_downgrade():
    verifier = FinVerifyLayer(FinGuardConfig())

    result = verifier.process(
        response="AAPL revenue was 100 in 2023 and operating margin was 30%.",
        sources=[
            {
                "source_id": "src_1",
                "title": "AAPL filing",
                "content": "AAPL revenue was 100 in 2023.",
                "url": "https://example.com/aapl",
            }
        ],
        query_type="factual",
        expected_behavior="answer_normally",
        finance_scope=True,
    )

    assert result.verification_status == "partially_verified"
    assert result.downgraded_for_verification is True
    assert result.supported_numbers == ["100", "2023"]
    assert result.unverified_numbers == ["30%"]
    assert result.final_response.startswith(
        "Based on the captured sources, some figures below remain unverified"
    )
    assert "Verification note: some numeric claims could not be verified" in result.final_response
    assert "Sources:" in result.final_response


def test_verify_refusal_branch_returns_not_applicable_status():
    verifier = FinVerifyLayer(FinGuardConfig())

    result = verifier.process(
        response="I can't provide that.",
        sources=[],
        query_type="compliance_sensitive",
        expected_behavior="refuse_with_disclaimer",
        finance_scope=True,
    )

    assert result.verification_status == "not_applicable"
    assert result.numeric_claim_count == 0
    assert result.downgraded_for_verification is False
