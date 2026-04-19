from finguard.config import FinGuardConfig
from finguard.fin_utils import normalize_sources
from finguard.fin_verify import FinVerifyLayer


def test_normalize_sources_from_messages_pairs_tool_calls():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"url":"https://example.com/aapl"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "AAPL revenue was 100 in 2023. https://example.com/aapl",
        },
    ]

    sources = normalize_sources(messages=messages)

    assert len(sources) == 1
    assert sources[0]["tool_name"] == "web_search"
    assert sources[0]["url"] == "https://example.com/aapl"


def test_verify_adds_disclaimer_and_sources():
    verifier = FinVerifyLayer(FinGuardConfig())
    result = verifier.process(
        response="AAPL revenue was 100 in 2023.",
        sources=[
            {
                "source_id": "src_1",
                "title": "AAPL 2023 filing",
                "content": "AAPL revenue was 100 in 2023.",
                "url": "https://example.com/aapl",
            }
        ],
        query_type="compliance_sensitive",
        expected_behavior="answer_with_disclaimer",
        finance_scope=True,
    )

    assert "Disclaimer:" in result.final_response
    assert "Sources:" in result.final_response
    assert result.unverified_numbers == []
    assert result.numeric_claim_count == 2


def test_normalize_sources_parses_json_string_payload():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": "{}",
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": '{"results":[{"title":"AAPL filing","content":"Revenue was 100.","url":"https://example.com/aapl"}]}',
        },
    ]

    sources = normalize_sources(messages=messages)

    assert len(sources) == 1
    assert sources[0]["title"] == "AAPL filing"
    assert sources[0]["url"] == "https://example.com/aapl"


def test_normalize_sources_merges_multiple_tool_messages_for_same_call():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"url":"https://example.com/aapl"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "Revenue was 100.",
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "Operating income was 20.",
        },
    ]

    sources = normalize_sources(messages=messages)

    assert len(sources) == 1
    assert "Revenue was 100." in sources[0]["content"]
    assert "Operating income was 20." in sources[0]["content"]


def test_normalize_sources_can_fallback_when_tool_call_id_is_missing():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"url":"https://example.com/aapl"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "content": "Revenue was 100. https://example.com/aapl",
        },
    ]

    sources = normalize_sources(messages=messages)

    assert len(sources) == 1
    assert sources[0]["tool_name"] == "web_search"
    assert sources[0]["url"] == "https://example.com/aapl"


def test_verify_marks_numeric_claims_unverified_when_no_sources_exist():
    verifier = FinVerifyLayer(FinGuardConfig())
    result = verifier.process(
        response="AAPL revenue was 100 in 2023.",
        sources=[],
        query_type="factual",
        expected_behavior="answer_normally",
        finance_scope=True,
    )

    assert result.numeric_claim_count == 2
    assert result.unverified_numbers == ["100", "2023"]
    assert "Verification note: no captured sources were available" in result.final_response


def test_normalize_sources_returns_empty_when_tools_never_reply():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": '{"url":"https://example.com/aapl"}',
                    },
                }
            ],
        }
    ]

    sources = normalize_sources(messages=messages)

    assert sources == []


def test_normalize_sources_can_capture_tool_reply_without_assistant_batch():
    messages = [
        {
            "role": "tool",
            "content": "Standalone tool output with revenue 100. https://example.com/aapl",
        }
    ]

    sources = normalize_sources(messages=messages)

    assert len(sources) == 1
    assert sources[0]["content"].startswith("Standalone tool output")
    assert sources[0]["url"] == "https://example.com/aapl"
    assert sources[0]["tool_name"] == ""


def test_normalize_sources_handles_mixed_json_text_and_empty_segments():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": "{}",
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": '{"results":[{"title":"AAPL filing","content":"Revenue was 100.","url":"https://example.com/aapl"}]}',
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "",
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "Trailing note about operating income.",
        },
    ]

    sources = normalize_sources(messages=messages)

    assert len(sources) == 2
    assert sources[0]["title"] == "AAPL filing"
    assert sources[1]["content"] == "Trailing note about operating income."


def test_normalize_sources_truncates_long_content():
    long_content = "A" * 50
    sources = normalize_sources(
        sources=[
            {
                "source_id": "src_1",
                "title": "long source",
                "content": long_content,
            }
        ],
        max_content_chars=12,
    )

    assert len(sources) == 1
    assert sources[0]["content"] == "A" * 12
