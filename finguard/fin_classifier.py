from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from finguard.config import FinGuardConfig

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


@dataclass
class ClassificationResult:
    query_type: QueryType
    expected_behavior: ExpectedBehavior
    confidence: float
    finance_scope: bool
    reasons: list[str] = field(default_factory=list)


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
        "tax",
        "taxes",
        "capital gains",
        "options",
        "equity",
        "financial",
    )

    _OPERATIONAL_PATTERNS = (
        re.compile(r"^\s*(buy|sell|short|rebalance|place|execute|transfer|withdraw|deposit)\b", re.I),
        re.compile(r"\b(place an order|execute (the )?trade|rebalance my portfolio|transfer funds)\b", re.I),
    )
    _DIRECT_ADVICE_PATTERNS = (
        re.compile(r"\bshould i\b", re.I),
        re.compile(r"\bdo you recommend\b", re.I),
        re.compile(r"\bwhat should i (buy|sell|invest in)\b", re.I),
        re.compile(r"\bis\b.+\ba good (investment|stock|buy)\b", re.I),
        re.compile(r"\bprice target\b", re.I),
        re.compile(r"\bfinancial advice\b", re.I),
    )
    _EDUCATIONAL_COMPLIANCE_PATTERNS = (
        re.compile(r"\b(explain|walk me through|how does|how do|compare|difference between)\b", re.I),
        re.compile(r"\b(risks of|pros and cons|what should investors consider)\b", re.I),
    )

    def __init__(self, config: FinGuardConfig):
        self.config = config

    def is_finance_related(self, query: str) -> bool:
        lowered = query.lower()
        return any(term in lowered for term in self._FINANCE_TERMS)

    def classify(self, query: str) -> ClassificationResult:
        text = (query or "").strip()
        lowered = text.lower()
        finance_scope = self.is_finance_related(lowered)
        reasons: list[str] = []

        if finance_scope and any(pattern.search(text) for pattern in self._OPERATIONAL_PATTERNS):
            reasons.append("matched operational finance pattern")
            return ClassificationResult(
                query_type="operational",
                expected_behavior="refuse_with_disclaimer",
                confidence=0.92,
                finance_scope=True,
                reasons=reasons,
            )

        if finance_scope and any(pattern.search(text) for pattern in self._DIRECT_ADVICE_PATTERNS):
            reasons.append("matched direct recommendation pattern")
            return ClassificationResult(
                query_type="compliance_sensitive",
                expected_behavior="refuse_with_disclaimer",
                confidence=0.94,
                finance_scope=True,
                reasons=reasons,
            )

        if finance_scope and any(pattern.search(text) for pattern in self._EDUCATIONAL_COMPLIANCE_PATTERNS):
            reasons.append("matched educational compliance pattern")
            return ClassificationResult(
                query_type="compliance_sensitive",
                expected_behavior="answer_with_disclaimer",
                confidence=0.78,
                finance_scope=True,
                reasons=reasons,
            )

        if self.config.strict_financial_scope and not finance_scope:
            reasons.append("strict financial scope enabled")
            return ClassificationResult(
                query_type="out_of_scope",
                expected_behavior="refuse_with_disclaimer",
                confidence=0.7,
                finance_scope=False,
                reasons=reasons,
            )

        if finance_scope:
            reasons.append("matched finance topic vocabulary")

        return ClassificationResult(
            query_type="factual",
            expected_behavior="answer_normally",
            confidence=0.6 if finance_scope else 0.55,
            finance_scope=finance_scope,
            reasons=reasons,
        )
