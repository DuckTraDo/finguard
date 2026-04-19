from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Literal

from finguard.config import FinGuardConfig
from finguard.fin_utils import TemporalIntent, build_temporal_intent, extract_time_context

QueryType = Literal[
    "factual",
    "compliance_sensitive",
    "operational",
    "out_of_scope",
    "injection",
]
ExpectedBehavior = Literal[
    "refuse_with_disclaimer",
    "answer_with_disclaimer",
    "answer_normally",
]

REASON_TEMPORAL_INTENT = "temporal.intent_detected"
REASON_PERSONAL_CONTEXT = "context.personal_finance"
REASON_OPERATIONAL_PATTERN = "pattern.operational_finance"
REASON_DIRECT_ADVICE_PATTERN = "pattern.direct_advice"
REASON_GENERAL_RECOMMENDATION_PATTERN = "pattern.general_recommendation"
REASON_EDUCATIONAL_PATTERN = "pattern.educational_finance"
REASON_STRICT_FINANCIAL_SCOPE = "scope.strict_financial_mode"
REASON_FACTUAL_PATTERN = "pattern.factual_finance_request"
REASON_FINANCE_TOPIC = "scope.finance_topic_vocabulary"
REASON_OPTIONAL_REFINER = "refiner.optional_classifier_refiner"


def _empty_temporal_intent() -> TemporalIntent:
    return {
        "detected": False,
        "signals": [],
        "requires_explicit_dates": False,
        "relative_terms": [],
        "years": [],
        "quarters": [],
    }


def _is_reason_tag(reason: str) -> bool:
    return bool(re.fullmatch(r"[a-z]+(?:\.[a-z0-9_]+)+", reason or ""))


@dataclass
class ClassificationResult:
    query_type: QueryType
    expected_behavior: ExpectedBehavior
    confidence: float
    finance_scope: bool
    temporal_intent: TemporalIntent = field(default_factory=_empty_temporal_intent)
    llm_refined: bool = False
    reasons: list[str] = field(default_factory=list)


ClassificationRefiner = Callable[[str, ClassificationResult], ClassificationResult | None]


class FinClassifier:
    _FINANCE_TERMS = (
        "stock",
        "stocks",
        "share",
        "shares",
        "bond",
        "bonds",
        "portfolio",
        "etf",
        "etfs",
        "revenue",
        "earnings",
        "ebitda",
        "balance sheet",
        "cash flow",
        "market cap",
        "dividend",
        "invest",
        "investment",
        "trading",
        "trade",
        "buy",
        "sell",
        "bull",
        "bear",
        "valuation",
        "price target",
        "10-k",
        "10-q",
        "sec",
        "edgar",
        "interest rate",
        "inflation",
        "yield",
        "default rate",
        "treasury",
        "credit spread",
        "fed",
        "cpi",
        "ppi",
        "tax",
        "taxes",
        "capital gains",
        "options",
        "equity",
        "financial",
        "brokerage",
        "asset allocation",
    )
    _TICKER_RE = re.compile(r"(?:\$)?\b[A-Z]{1,5}\b")
    _TICKER_STOPWORDS = {
        "A",
        "I",
        "USD",
        "ETF",
        "EPS",
        "CPI",
        "PPI",
        "GDP",
        "APR",
        "IRA",
        "ROI",
    }

    _TEMPORAL_PATTERNS = (
        re.compile(r"\b(today|tomorrow|yesterday|current|currently|latest|most recent|now|as of)\b", re.I),
        re.compile(r"\b(this|next|last)\s+(week|month|quarter|year)\b", re.I),
        re.compile(r"\b(recent|upcoming|year[- ]to[- ]date|month[- ]to[- ]date|week[- ]to[- ]date)\b", re.I),
    )
    _OPERATIONAL_PATTERNS = (
        re.compile(r"^\s*(buy|sell|short|rebalance|place|execute|transfer|withdraw|deposit|allocate|set)\b", re.I),
        re.compile(r"\b(place an order|execute (the )?trade|rebalance (my )?portfolio|transfer funds)\b", re.I),
        re.compile(r"\b(open|close|exit)\s+(a|my)\s+position\b", re.I),
        re.compile(r"\bset (a )?(stop loss|take profit)\b", re.I),
        re.compile(r"\b(sell|buy)\s+\d+\s+(share|shares|contract|contracts)\b", re.I),
        re.compile(r"\bmove money\b|\bmove cash\b|\bdeposit funds\b", re.I),
    )
    _DIRECT_ADVICE_PATTERNS = (
        re.compile(r"\bshould i\b", re.I),
        re.compile(r"\bdo you recommend\b", re.I),
        re.compile(r"\bwhat should i (buy|sell|invest in)\b", re.I),
        re.compile(r"\bis\b.+\ba good (investment|stock|buy)\b", re.I),
        re.compile(r"\bworth (buying|investing in)\b", re.I),
        re.compile(r"\bprice target\b", re.I),
        re.compile(r"\bfinancial advice\b", re.I),
        re.compile(r"\bwhat should i do with\b", re.I),
    )
    _GENERAL_RECOMMENDATION_PATTERNS = (
        re.compile(r"\b(best|top)\s+\w*\s*(stock|stocks|etf|etfs|fund|funds|bond|bonds)\b", re.I),
        re.compile(r"\bwhich\s+\w*\s*(stock|stocks|etf|etfs|fund|funds|bond|bonds)\b", re.I),
        re.compile(r"\bwhat are good\b.+\b(stock|stocks|etf|etfs|funds|bonds)\b", re.I),
    )
    _EDUCATIONAL_COMPLIANCE_PATTERNS = (
        re.compile(r"\b(explain|walk me through|how does|how do|compare|difference between|pros and cons)\b", re.I),
        re.compile(r"\b(risks of|what should investors consider|things investors should consider)\b", re.I),
        re.compile(r"\bfor a beginner\b", re.I),
    )
    _MARKET_DATA_PATTERNS = (
        re.compile(r"^\s*(what|when|which|who|how much|how many|summarize|describe|define)\b", re.I),
        re.compile(r"\b(revenue|earnings|yield|inflation|default rate|filing|market cap|cash flow)\b", re.I),
    )
    _PERSONAL_CONTEXT_PATTERNS = (
        re.compile(r"\b(my|for me|my account|my portfolio|my retirement|my savings)\b", re.I),
        re.compile(r"\bI (own|hold|bought|sold|am considering)\b", re.I),
    )

    def __init__(
        self,
        config: FinGuardConfig,
        decision_refiner: ClassificationRefiner | None = None,
    ):
        self.config = config
        self.decision_refiner = decision_refiner

    def is_finance_related(self, query: str) -> bool:
        text = query or ""
        lowered = text.lower()
        if any(term in lowered for term in self._FINANCE_TERMS):
            return True

        for token in self._TICKER_RE.findall(text):
            clean = token.lstrip("$").upper()
            if clean not in self._TICKER_STOPWORDS:
                return True
        return False

    def has_temporal_intent(self, query: str) -> bool:
        return bool(self.temporal_intent_schema(query)["detected"])

    def temporal_intent_schema(self, query: str) -> TemporalIntent:
        text = query or ""
        time_context = extract_time_context(text)
        if time_context:
            return build_temporal_intent(time_context)

        signals: list[str] = []
        for pattern in self._TEMPORAL_PATTERNS:
            if pattern.search(text):
                signals.append("relative_time")
                break

        return {
            "detected": bool(signals),
            "signals": signals,
            "requires_explicit_dates": bool(signals),
            "relative_terms": [],
            "years": [],
            "quarters": [],
        }

    def classify(self, query: str) -> ClassificationResult:
        text = (query or "").strip()
        finance_scope = self.is_finance_related(text)
        temporal_intent = self.temporal_intent_schema(text)
        temporal_detected = bool(temporal_intent["detected"])
        reasons: list[str] = []

        if temporal_detected:
            reasons.append(REASON_TEMPORAL_INTENT)

        if finance_scope and any(pattern.search(text) for pattern in self._OPERATIONAL_PATTERNS):
            reasons.append(REASON_OPERATIONAL_PATTERN)
            return self._build_result(
                query_type="operational",
                expected_behavior="refuse_with_disclaimer",
                confidence=0.95,
                finance_scope=True,
                temporal_intent=temporal_intent,
                reasons=reasons,
            )

        personal_context = any(pattern.search(text) for pattern in self._PERSONAL_CONTEXT_PATTERNS)
        if personal_context:
            reasons.append(REASON_PERSONAL_CONTEXT)

        if finance_scope and any(pattern.search(text) for pattern in self._DIRECT_ADVICE_PATTERNS):
            reasons.append(REASON_DIRECT_ADVICE_PATTERN)
            return self._build_result(
                query_type="compliance_sensitive",
                expected_behavior="refuse_with_disclaimer",
                confidence=0.96,
                finance_scope=True,
                temporal_intent=temporal_intent,
                reasons=reasons,
            )

        if finance_scope and any(pattern.search(text) for pattern in self._GENERAL_RECOMMENDATION_PATTERNS):
            reasons.append(REASON_GENERAL_RECOMMENDATION_PATTERN)
            return self._build_result(
                query_type="compliance_sensitive",
                expected_behavior="refuse_with_disclaimer" if personal_context else "answer_with_disclaimer",
                confidence=0.86 if personal_context else 0.81,
                finance_scope=True,
                temporal_intent=temporal_intent,
                reasons=reasons,
            )

        if finance_scope and any(pattern.search(text) for pattern in self._EDUCATIONAL_COMPLIANCE_PATTERNS):
            reasons.append(REASON_EDUCATIONAL_PATTERN)
            return self._build_result(
                query_type="compliance_sensitive",
                expected_behavior="answer_with_disclaimer",
                confidence=0.82,
                finance_scope=True,
                temporal_intent=temporal_intent,
                reasons=reasons,
            )

        if self.config.strict_financial_scope and not finance_scope:
            reasons.append(REASON_STRICT_FINANCIAL_SCOPE)
            return self._build_result(
                query_type="out_of_scope",
                expected_behavior="refuse_with_disclaimer",
                confidence=0.72,
                finance_scope=False,
                temporal_intent=temporal_intent,
                reasons=reasons,
            )

        if finance_scope and any(pattern.search(text) for pattern in self._MARKET_DATA_PATTERNS):
            reasons.append(REASON_FACTUAL_PATTERN)
            base = self._build_result(
                query_type="factual",
                expected_behavior="answer_normally",
                confidence=0.83 if temporal_detected else 0.8,
                finance_scope=True,
                temporal_intent=temporal_intent,
                reasons=reasons,
            )
        else:
            if finance_scope:
                reasons.append(REASON_FINANCE_TOPIC)
            base = self._build_result(
                query_type="factual",
                expected_behavior="answer_normally",
                confidence=0.68 if finance_scope else 0.55,
                finance_scope=finance_scope,
                temporal_intent=temporal_intent,
                reasons=reasons,
            )

        return self._maybe_refine(query=text, base_result=base)

    def _build_result(
        self,
        query_type: QueryType,
        expected_behavior: ExpectedBehavior,
        confidence: float,
        finance_scope: bool,
        temporal_intent: TemporalIntent,
        reasons: list[str],
        llm_refined: bool = False,
    ) -> ClassificationResult:
        return ClassificationResult(
            query_type=query_type,
            expected_behavior=expected_behavior,
            confidence=confidence,
            finance_scope=finance_scope,
            temporal_intent=temporal_intent,
            llm_refined=llm_refined,
            reasons=list(reasons),
        )

    def _maybe_refine(self, query: str, base_result: ClassificationResult) -> ClassificationResult:
        if not self.config.enable_llm_classifier_refiner:
            return base_result
        if self.decision_refiner is None:
            return base_result
        if base_result.confidence >= self.config.classifier_refiner_confidence_floor:
            return base_result

        try:
            refined = self.decision_refiner(query, base_result)
        except Exception:
            return base_result

        if refined is None:
            return base_result

        reasons = list(base_result.reasons)
        reasons.extend(
            reason
            for reason in refined.reasons
            if _is_reason_tag(reason) and reason not in reasons
        )
        if REASON_OPTIONAL_REFINER not in reasons:
            reasons.append(REASON_OPTIONAL_REFINER)
        return ClassificationResult(
            query_type=refined.query_type,
            expected_behavior=refined.expected_behavior,
            confidence=max(refined.confidence, base_result.confidence),
            finance_scope=bool(refined.finance_scope or base_result.finance_scope),
            temporal_intent=_merge_temporal_intent(base_result.temporal_intent, refined.temporal_intent),
            llm_refined=True,
            reasons=reasons,
        )


def _merge_temporal_intent(base: TemporalIntent, refined: TemporalIntent) -> TemporalIntent:
    merged_signals = list(dict.fromkeys(list(base.get("signals", [])) + list(refined.get("signals", []))))
    merged_relative_terms = list(
        dict.fromkeys(list(base.get("relative_terms", [])) + list(refined.get("relative_terms", [])))
    )
    merged_years = list(dict.fromkeys(list(base.get("years", [])) + list(refined.get("years", []))))
    merged_quarters = list(
        dict.fromkeys(list(base.get("quarters", [])) + list(refined.get("quarters", [])))
    )
    return {
        "detected": bool(base.get("detected") or refined.get("detected")),
        "signals": merged_signals,
        "requires_explicit_dates": bool(
            base.get("requires_explicit_dates") or refined.get("requires_explicit_dates")
        ),
        "relative_terms": merged_relative_terms,
        "years": merged_years,
        "quarters": merged_quarters,
    }
