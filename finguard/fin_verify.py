from __future__ import annotations

from dataclasses import dataclass

from finguard.config import FinGuardConfig
from finguard.fin_classifier import ExpectedBehavior, QueryType
from finguard.fin_utils import (
    append_sources_section,
    build_refusal_response,
    citation_entries_from_sources,
    ensure_disclaimer,
    extract_numbers,
    normalize_sources,
    number_is_supported,
    response_has_refusal_language,
)


@dataclass
class VerifyResult:
    final_response: str
    unverified_numbers: list[str]
    citations: list[dict]
    disclaimer_added: bool
    hallucination_risk_score: float
    numeric_claim_count: int


class FinVerifyLayer:
    def __init__(self, config: FinGuardConfig):
        self.config = config

    def process(
        self,
        response: str,
        sources,
        query_type: QueryType,
        expected_behavior: ExpectedBehavior = "answer_normally",
        finance_scope: bool = True,
    ) -> VerifyResult:
        if not finance_scope and query_type == "factual":
            return VerifyResult(
                final_response=response,
                unverified_numbers=[],
                citations=[],
                disclaimer_added=False,
                hallucination_risk_score=0.0,
                numeric_claim_count=0,
            )

        normalized_sources = normalize_sources(sources=sources)
        citations = citation_entries_from_sources(normalized_sources)
        unverified_numbers: list[str] = []
        disclaimer_added = False
        final_response = (response or "").strip()

        if expected_behavior == "refuse_with_disclaimer":
            if not response_has_refusal_language(final_response):
                final_response = build_refusal_response(
                    "I can't provide a personalized financial recommendation",
                    self.config.compliance_disclaimer,
                )
                disclaimer_added = True
            else:
                final_response, disclaimer_added = ensure_disclaimer(
                    final_response,
                    self.config.compliance_disclaimer,
                )
            return VerifyResult(
                final_response=final_response,
                unverified_numbers=[],
                citations=[],
                disclaimer_added=disclaimer_added,
                hallucination_risk_score=0.0,
            )

        if query_type == "compliance_sensitive" or expected_behavior == "answer_with_disclaimer":
            final_response, disclaimer_added = ensure_disclaimer(
                final_response,
                self.config.compliance_disclaimer,
            )

        numbers = extract_numbers(final_response)
        numeric_claim_count = len(numbers)
        for token in numbers:
            if not number_is_supported(token, normalized_sources):
                unverified_numbers.append(token)

        hallucination_risk_score = (
            len(unverified_numbers) / numeric_claim_count
            if numeric_claim_count
            else 0.0
        )

        if citations:
            final_response = append_sources_section(final_response, citations)

        if unverified_numbers:
            preview = ", ".join(unverified_numbers[:5])
            if normalized_sources:
                note = (
                    "Verification note: some numeric claims could not be verified "
                    f"from the captured sources ({preview})."
                )
            else:
                note = (
                    "Verification note: no captured sources were available to verify "
                    f"numeric claims ({preview})."
                )
            final_response = f"{final_response}\n\n{note}"

        return VerifyResult(
            final_response=final_response,
            unverified_numbers=unverified_numbers,
            citations=citations,
            disclaimer_added=disclaimer_added,
            hallucination_risk_score=hallucination_risk_score,
            numeric_claim_count=numeric_claim_count,
        )
