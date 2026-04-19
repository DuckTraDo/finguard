from __future__ import annotations

import json
import re
from typing import Any, Iterable, Sequence

from finguard.fin_classifier import ExpectedBehavior, QueryType

_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[$€£])?\d[\d,]*(?:\.\d+)?(?:\s?(?:%|bps|bp|million|billion|trillion|m|bn|k))?(?![A-Za-z0-9])",
    re.I,
)
_URL_RE = re.compile(r"https?://\S+", re.I)
_RELATIVE_TIME_RE = re.compile(
    r"\b(today|tomorrow|yesterday|current|currently|latest|most recent|now|as of)\b",
    re.I,
)
_DATE_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_QUARTER_RE = re.compile(r"\bq([1-4])\s*(20\d{2})\b", re.I)


def extract_time_context(query: str) -> dict[str, Any] | None:
    text = (query or "").strip()
    if not text:
        return None

    relative_terms = [match.group(0).lower() for match in _RELATIVE_TIME_RE.finditer(text)]
    years = sorted({match.group(1) for match in _DATE_RE.finditer(text)})
    quarters = [f"Q{match.group(1)} {match.group(2)}" for match in _QUARTER_RE.finditer(text)]

    if not relative_terms and not years and not quarters:
        return None

    return {
        "relative_terms": relative_terms,
        "years": years,
        "quarters": quarters,
        "requires_explicit_dates": bool(relative_terms),
    }


def build_augmented_query(
    query: str,
    query_type: QueryType,
    expected_behavior: ExpectedBehavior,
    finance_scope: bool,
    time_context: dict[str, Any] | None,
) -> str:
    if not finance_scope and not time_context:
        return query

    notes: list[str] = []
    if query_type == "compliance_sensitive" and expected_behavior == "answer_with_disclaimer":
        notes.append(
            "Answer in an educational, non-personalized way. Avoid recommendations or individualized advice."
        )
    if time_context and time_context.get("requires_explicit_dates"):
        notes.append("Use explicit dates in the answer and be careful with time-sensitive claims.")

    if not notes:
        return query

    return f"{query}\n\n[FinGuard context]\n" + "\n".join(f"- {note}" for note in notes)


def build_refusal_response(reason: str, disclaimer: str) -> str:
    reason_text = reason.strip().rstrip(".") if reason else "I can't help with that request"
    if disclaimer:
        return f"{reason_text}.\n\nDisclaimer: {disclaimer}"
    return f"{reason_text}."


def extract_numbers(text: str) -> list[str]:
    if not text:
        return []
    return [match.group(0).strip() for match in _NUMBER_RE.finditer(text)]


def _canonical_number_token(token: str) -> str:
    return re.sub(r"[^0-9.%]", "", token.lower())


def number_is_supported(token: str, sources: Sequence[dict[str, Any]]) -> bool:
    canonical = _canonical_number_token(token)
    if not canonical:
        return False

    for source in sources:
        content = str(source.get("content", ""))
        if token in content:
            return True
        if canonical and canonical in _canonical_number_token(content):
            return True
    return False


def response_has_refusal_language(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        phrase in lowered
        for phrase in (
            "can't provide",
            "cannot provide",
            "can't recommend",
            "cannot recommend",
            "not able to recommend",
            "can't execute",
            "cannot execute",
        )
    )


def ensure_disclaimer(text: str, disclaimer: str) -> tuple[str, bool]:
    if not disclaimer:
        return text, False
    if disclaimer.lower() in (text or "").lower():
        return text, False
    separator = "\n\n" if text and not text.endswith("\n") else ""
    return f"{text}{separator}Disclaimer: {disclaimer}".strip(), True


def append_sources_section(text: str, citations: Sequence[dict[str, Any]]) -> str:
    if not citations or "sources:" in (text or "").lower():
        return text

    lines = []
    for citation in citations:
        label = citation.get("title") or citation.get("source_id") or "source"
        url = citation.get("url")
        if url:
            lines.append(f"- {label} ({url})")
        else:
            lines.append(f"- {label}")

    return f"{text.rstrip()}\n\nSources:\n" + "\n".join(lines)


def citation_entries_from_sources(sources: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for source in sources:
        title = str(source.get("title") or source.get("tool_name") or "source")
        url = str(source.get("url") or "")
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "source_id": source.get("source_id") or title,
                "title": title,
                "url": url,
            }
        )
    return citations


def normalize_sources(
    sources: Any = None,
    messages: Sequence[dict[str, Any]] | None = None,
    max_content_chars: int = 4000,
) -> list[dict[str, Any]]:
    if isinstance(sources, list):
        normalized: list[dict[str, Any]] = []
        for idx, item in enumerate(sources):
            normalized.extend(
                _coerce_source_payload(
                    payload=item,
                    defaults={"source_id": f"source_{idx}"},
                    max_content_chars=max_content_chars,
                )
            )
        return _dedupe_sources(normalized)

    if messages:
        return _dedupe_sources(
            normalize_sources_from_messages(messages, max_content_chars=max_content_chars)
        )

    if sources is not None:
        return _dedupe_sources(
            _coerce_source_payload(
                payload=sources,
                defaults={"source_id": "source_0"},
                max_content_chars=max_content_chars,
            )
        )

    return []


def normalize_sources_from_messages(
    messages: Sequence[dict[str, Any]],
    max_content_chars: int = 4000,
) -> list[dict[str, Any]]:
    grouped_payloads: dict[str, dict[str, Any]] = {}
    current_batch: list[dict[str, Any]] = []
    batch_cursor = 0

    for message in messages:
        if message.get("role") == "assistant":
            current_batch = _extract_tool_batch(message.get("tool_calls") or [])
            batch_cursor = 0
            continue

        if message.get("role") != "tool":
            current_batch = []
            batch_cursor = 0
            continue

        resolved = _resolve_tool_message_context(message, current_batch, batch_cursor, len(grouped_payloads))
        batch_cursor = resolved["next_batch_cursor"]
        source_id = resolved["source_id"]
        group = grouped_payloads.setdefault(
            source_id,
            {
                "defaults": resolved["defaults"],
                "payloads": [],
            },
        )
        group["defaults"] = _merge_defaults(group["defaults"], resolved["defaults"])
        group["payloads"].append(message.get("content", ""))

    normalized: list[dict[str, Any]] = []
    for group in grouped_payloads.values():
        merged_payload = _merge_payloads(group["payloads"])
        normalized.extend(
            _coerce_source_payload(
                payload=merged_payload,
                defaults=group["defaults"],
                max_content_chars=max_content_chars,
            )
        )
    return normalized


def _extract_tool_batch(tool_calls: Sequence[Any]) -> list[dict[str, Any]]:
    batch: list[dict[str, Any]] = []
    for idx, tool_call in enumerate(tool_calls):
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function") or {}
        arguments = function.get("arguments") or "{}"
        parsed_arguments = _maybe_json_load(arguments)
        batch.append(
            {
                "id": str(tool_call.get("id") or tool_call.get("call_id") or f"tool_call_{idx}"),
                "tool_name": str(function.get("name") or "tool"),
                "arguments": parsed_arguments if isinstance(parsed_arguments, dict) else {},
            }
        )
    return batch


def _resolve_tool_message_context(
    message: dict[str, Any],
    current_batch: Sequence[dict[str, Any]],
    batch_cursor: int,
    synthetic_index: int,
) -> dict[str, Any]:
    explicit_tool_call_id = str(message.get("tool_call_id") or "")
    matched_meta = None
    next_batch_cursor = batch_cursor

    if explicit_tool_call_id:
        matched_meta = next(
            (entry for entry in current_batch if entry.get("id") == explicit_tool_call_id),
            None,
        )
    elif batch_cursor < len(current_batch):
        matched_meta = current_batch[batch_cursor]
        explicit_tool_call_id = str(matched_meta.get("id") or f"tool_{synthetic_index}")
        next_batch_cursor += 1
    else:
        explicit_tool_call_id = f"tool_{synthetic_index}"

    defaults = {
        "source_id": explicit_tool_call_id or f"tool_{synthetic_index}",
        "title": "tool result",
        "content": str(message.get("content", "")),
        "url": "",
        "timestamp": "",
        "span": "",
        "tool_name": "",
    }

    if matched_meta:
        defaults["tool_name"] = str(matched_meta.get("tool_name") or "")
        defaults["title"] = defaults["tool_name"] or defaults["title"]
        args = matched_meta.get("arguments") or {}
        if isinstance(args, dict):
            defaults["url"] = str(
                args.get("url")
                or args.get("link")
                or args.get("source_url")
                or ""
            )

    return {
        "source_id": defaults["source_id"],
        "defaults": defaults,
        "next_batch_cursor": next_batch_cursor,
    }


def _merge_defaults(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key not in merged or not merged[key]:
            merged[key] = value
    return merged


def _merge_payloads(payloads: Sequence[Any]) -> Any:
    parsed_items = []
    raw_texts = []

    for payload in payloads:
        parsed = _maybe_json_load(payload)
        if isinstance(parsed, list):
            parsed_items.extend(parsed)
        elif isinstance(parsed, dict):
            parsed_items.append(parsed)
        else:
            text = str(payload or "").strip()
            if text:
                raw_texts.append(text)

    if parsed_items and not raw_texts:
        return parsed_items
    if parsed_items and raw_texts:
        return parsed_items + [{"content": "\n\n".join(raw_texts)}]
    return "\n\n".join(raw_texts)


def _coerce_source_payload(
    payload: Any,
    defaults: dict[str, Any],
    max_content_chars: int,
) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        entries = payload.get("results") if isinstance(payload.get("results"), list) else None
        if entries is None:
            entries = payload.get("items") if isinstance(payload.get("items"), list) else None
        if entries is None:
            entries = [payload]
        return [
            _coerce_source_entry(entry, defaults, idx, max_content_chars)
            for idx, entry in enumerate(entries)
        ]

    if isinstance(payload, list):
        flattened_entries: list[Any] = []
        for entry in payload:
            if isinstance(entry, dict):
                nested_entries = (
                    entry.get("results")
                    if isinstance(entry.get("results"), list)
                    else entry.get("items")
                    if isinstance(entry.get("items"), list)
                    else None
                )
                if nested_entries is not None:
                    flattened_entries.extend(nested_entries)
                    continue
            flattened_entries.append(entry)
        return [
            _coerce_source_entry(entry, defaults, idx, max_content_chars)
            for idx, entry in enumerate(flattened_entries)
        ]

    if isinstance(payload, str):
        parsed = _maybe_json_load(payload)
        if parsed is not None and parsed is not payload:
            return _coerce_source_payload(parsed, defaults, max_content_chars)

    return [_coerce_source_entry(payload, defaults, 0, max_content_chars)]


def _coerce_source_entry(
    entry: Any,
    defaults: dict[str, Any],
    idx: int,
    max_content_chars: int,
) -> dict[str, Any]:
    if isinstance(entry, dict):
        content = (
            entry.get("content")
            or entry.get("text")
            or entry.get("body")
            or entry.get("snippet")
            or entry.get("summary")
            or entry.get("result")
            or defaults.get("content", "")
        )
        title = (
            entry.get("title")
            or entry.get("name")
            or entry.get("source")
            or defaults.get("title", "source")
        )
        url = (
            entry.get("url")
            or entry.get("source_url")
            or entry.get("link")
            or defaults.get("url", "")
        )
        timestamp = (
            entry.get("timestamp")
            or entry.get("date")
            or entry.get("published")
            or defaults.get("timestamp", "")
        )
        span = entry.get("span") or entry.get("excerpt") or defaults.get("span", "")
    else:
        content = entry
        title = defaults.get("title", "source")
        url = defaults.get("url", "")
        timestamp = defaults.get("timestamp", "")
        span = defaults.get("span", "")

    text = str(content or "")
    if not url:
        url_match = _URL_RE.search(text)
        if url_match:
            url = url_match.group(0)

    return {
        "source_id": f"{defaults.get('source_id', 'source')}_{idx}",
        "title": str(title or "source"),
        "content": text[:max_content_chars],
        "url": str(url or ""),
        "timestamp": str(timestamp or ""),
        "span": str(span or ""),
        "tool_name": str(defaults.get("tool_name", "")),
    }


def _maybe_json_load(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except Exception:
        return value


def _dedupe_sources(sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source in sources:
        key = (
            str(source.get("title", "")),
            str(source.get("url", "")),
            str(source.get("content", ""))[:200],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped
