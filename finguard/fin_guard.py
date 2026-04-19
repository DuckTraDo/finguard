from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from finguard.config import FinGuardConfig
from finguard.fin_classifier import ExpectedBehavior, FinClassifier, QueryType
from finguard.fin_utils import build_augmented_query, extract_time_context


@dataclass
class GuardResult:
    passed: bool
    query_type: QueryType
    expected_behavior: ExpectedBehavior
    finance_scope: bool
    time_context: Optional[dict]
    refusal_reason: Optional[str]
    augmented_query: str


class FinGuardLayer:
    _INJECTION_PATTERNS = (
        re.compile(r"\bignore (all|previous|prior|above) instructions\b", re.I),
        re.compile(r"\bsystem prompt\b", re.I),
        re.compile(r"\bdeveloper message\b", re.I),
        re.compile(r"\bpretend to be\b", re.I),
        re.compile(r"\brole:? ?system\b", re.I),
    )

    def __init__(self, config: FinGuardConfig):
        self.config = config
        self.classifier = FinClassifier(config)

    def process(self, query: str) -> GuardResult:
        if self._detect_injection(query):
            return GuardResult(
                passed=False,
                query_type="injection",
                expected_behavior="refuse_with_disclaimer",
                finance_scope=self.classifier.is_finance_related(query),
                time_context=None,
                refusal_reason="I can't comply with instructions that attempt to override system or safety rules",
                augmented_query=query,
            )

        classification = self.classifier.classify(query)
        time_context = extract_time_context(query)

        if classification.query_type == "operational":
            return GuardResult(
                passed=False,
                query_type=classification.query_type,
                expected_behavior=classification.expected_behavior,
                finance_scope=classification.finance_scope,
                time_context=time_context,
                refusal_reason="I can't execute trades, transfers, or other financial operations",
                augmented_query=query,
            )

        if classification.query_type == "out_of_scope":
            return GuardResult(
                passed=False,
                query_type=classification.query_type,
                expected_behavior=classification.expected_behavior,
                finance_scope=classification.finance_scope,
                time_context=time_context,
                refusal_reason="I can only help with finance-related analysis in this mode",
                augmented_query=query,
            )

        if classification.expected_behavior == "refuse_with_disclaimer":
            return GuardResult(
                passed=False,
                query_type=classification.query_type,
                expected_behavior=classification.expected_behavior,
                finance_scope=classification.finance_scope,
                time_context=time_context,
                refusal_reason="I can't provide a personalized financial recommendation",
                augmented_query=query,
            )

        augmented_query = query
        if self.config.augment_queries:
            augmented_query = build_augmented_query(
                query=query,
                query_type=classification.query_type,
                expected_behavior=classification.expected_behavior,
                finance_scope=classification.finance_scope,
                time_context=time_context,
            )

        return GuardResult(
            passed=True,
            query_type=classification.query_type,
            expected_behavior=classification.expected_behavior,
            finance_scope=classification.finance_scope,
            time_context=time_context,
            refusal_reason=None,
            augmented_query=augmented_query,
        )

    def _detect_injection(self, query: str) -> bool:
        return any(pattern.search(query or "") for pattern in self._INJECTION_PATTERNS)
