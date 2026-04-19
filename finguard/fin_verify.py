from __future__ import annotations

from dataclasses import dataclass

from finguard.config import FinGuardConfig
from finguard.fin_classifier import ExpectedBehavior, QueryType
from finguard.fin_utils import (
    append_sources_section,
    build_refusal_response,
    citation_entries_from_sources,
    ensure_disclaimer,
    ensure_verification_caveat,
    extract_numbers,
    normalize_sources,
    number_is_supported,
    response_has_refusal_language,
    supporting_sources_for_number,
)


@dataclass
class VerifyResult:
    final_response: str
    unverified_numbers: list[str]
    supported_numbers: list[str]
    citations: list[dict]
    disclaimer_added: bool
    hallucination_risk_score: float
    numeric_claim_count: int
    verification_status: str
    downgraded_for_verification: bool


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
                supported_numbers=[],
                citations=[],
                disclaimer_added=False,
                hallucination_risk_score=0.0,
                numeric_claim_count=0,
                verification_status="not_applicable",
                downgraded_for_verification=False,
            )

        normalized_sources = normalize_sources(sources=sources)
        citations = citation_entries_from_sources(normalized_sources)
        unverified_numbers: list[str] = []
        supported_numbers: list[str] = []
        disclaimer_added = False
        downgraded_for_verification = False
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
                supported_numbers=[],
                citations=[],
                disclaimer_added=disclaimer_added,
                hallucination_risk_score=0.0,
                numeric_claim_count=0,
                verification_status="not_applicable",
                downgraded_for_verification=False,
            )

        if query_type == "compliance_sensitive" or expected_behavior == "answer_with_disclaimer":
            final_response, disclaimer_added = ensure_disclaimer(
                final_response,
                self.config.compliance_disclaimer,
            )

        numbers = extract_numbers(final_response)
        numeric_claim_count = len(numbers)
        for token in numbers:
            if supporting_sources_for_number(token, normalized_sources):
                supported_numbers.append(token)
            else:
                unverified_numbers.append(token)

        hallucination_risk_score = (
            len(unverified_numbers) / numeric_claim_count
            if numeric_claim_count
            else 0.0
        )
        verification_status = self._verification_status(
            numeric_claim_count=numeric_claim_count,
            supported_numbers=supported_numbers,
            unverified_numbers=unverified_numbers,
            sources=normalized_sources,
        )

        caveat = self._build_verification_caveat(
            verification_status=verification_status,
            sources=normalized_sources,
            hallucination_risk_score=hallucination_risk_score,
        )
        if caveat:
            final_response, downgraded_for_verification = ensure_verification_caveat(
                final_response,
                caveat,
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
            supported_numbers=supported_numbers,
            citations=citations,
            disclaimer_added=disclaimer_added,
            hallucination_risk_score=hallucination_risk_score,
            numeric_claim_count=numeric_claim_count,
            verification_status=verification_status,
            downgraded_for_verification=downgraded_for_verification,
        )

    def _verification_status(
        self,
        numeric_claim_count: int,
        supported_numbers: list[str],
        unverified_numbers: list[str],
        sources,
    ) -> str:
        if numeric_claim_count == 0:
            return "not_applicable"
        if not unverified_numbers:
            return "verified"
        if not sources or not supported_numbers:
            return "unverified"
        return "partially_verified"

    def _build_verification_caveat(
        self,
        verification_status: str,
        sources,
        hallucination_risk_score: float,
    ) -> str:
        if verification_status == "unverified":
            if sources:
                return (
                    "I could not verify the specific figures below from the captured sources."
                )
            return (
                "I could not verify the specific figures below because no captured sources were available."
            )

        if (
            verification_status == "partially_verified"
            and hallucination_risk_score >= self.config.hallucination_risk_threshold
        ):
            return (
                "Based on the captured sources, some figures below remain unverified, "
                "so treat the specific numbers cautiously."
            )

        return ""
