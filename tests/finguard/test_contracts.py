from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from run_agent import AIAgent

EXPECTED_FINGUARD_KEYS = {
    "enabled",
    "guard_enabled",
    "verify_enabled",
    "passed",
    "query_type",
    "expected_behavior",
    "finance_scope",
    "time_context",
    "refusal_reason",
    "query_augmented",
    "source_count",
    "unverified_numbers",
    "numeric_claim_count",
    "verified_number_count",
    "hallucination_risk_score",
    "citations",
    "guard_status",
    "guard_error",
    "guard_latency_ms",
    "verify_status",
    "verify_error",
    "verify_latency_ms",
}


def _make_tool_defs(*names: str) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"{name} tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for name in names
    ]


def _mock_response(content: str = "Hello", finish_reason: str = "stop", tool_calls=None):
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
        refusal=None,
        reasoning_content=None,
    )
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(
        choices=[choice],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        model="test-model",
        id="test-id",
    )


@pytest.fixture()
def agent():
    with (
        patch("run_agent.get_tool_definitions", return_value=_make_tool_defs("web_search")),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = MagicMock()
        agent._cached_system_prompt = "You are helpful."
        agent._use_prompt_caching = False
        agent.tool_delay = 0
        agent.compression_enabled = False
        agent.save_trajectories = False
        return agent


def test_blocked_result_contract_is_stable(agent):
    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("Should I buy AAPL right now?")

    assert isinstance(result["final_response"], str)
    assert isinstance(result["messages"], list)
    assert isinstance(result["sources"], list)
    assert isinstance(result["finguard"], dict)
    assert set(result["finguard"].keys()) == EXPECTED_FINGUARD_KEYS
    assert result["finguard"]["enabled"] is True
    assert result["finguard"]["passed"] is False
    assert result["finguard"]["query_type"] == "compliance_sensitive"
    assert result["finguard"]["expected_behavior"] == "refuse_with_disclaimer"
    assert result["finguard"]["query_augmented"] is False
    assert result["finguard"]["guard_status"] == "ok"
    assert result["finguard"]["verify_status"] == "skipped"
    assert result["finguard"]["source_count"] == 0
    assert result["finguard"]["guard_latency_ms"] is not None
    assert result["finguard"]["verify_latency_ms"] is None


def test_augmented_query_does_not_pollute_returned_messages(agent):
    agent.client.chat.completions.create.return_value = _mock_response(
        content="Investors should consider valuation and cash flow.",
        finish_reason="stop",
    )

    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("Explain the risks of buying AAPL today.")

    user_messages = [msg for msg in result["messages"] if msg.get("role") == "user"]
    assert user_messages
    assert set(result["finguard"].keys()) == EXPECTED_FINGUARD_KEYS
    assert user_messages[0]["content"] == "Explain the risks of buying AAPL today."
    assert result["finguard"]["query_augmented"] is True
    assert result["finguard"]["guard_status"] == "ok"
    assert result["finguard"]["verify_status"] == "ok"
    assert isinstance(result["sources"], list)


def test_sources_is_always_list_when_no_tools_used(agent):
    agent.client.chat.completions.create.return_value = _mock_response(
        content="AAPL revenue was 100 in 2023.",
        finish_reason="stop",
    )

    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("What was AAPL revenue in 2023?")

    assert isinstance(result["sources"], list)
    assert result["sources"] == []
    assert set(result["finguard"].keys()) == EXPECTED_FINGUARD_KEYS
    assert result["finguard"]["source_count"] == 0
    assert result["finguard"]["verify_status"] == "ok"
    assert result["finguard"]["numeric_claim_count"] == 2
    assert result["finguard"]["verified_number_count"] == 0
    assert result["finguard"]["unverified_numbers"] == ["100", "2023"]


def test_guard_failure_keeps_contract_stable(agent):
    agent.client.chat.completions.create.return_value = _mock_response(
        content="Fallback answer.",
        finish_reason="stop",
    )

    with (
        patch.object(agent._finguard_guard, "process", side_effect=RuntimeError("guard-boom")),
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("What was AAPL revenue in 2023?")

    assert result["final_response"] == "Fallback answer."
    assert set(result["finguard"].keys()) == EXPECTED_FINGUARD_KEYS
    assert result["finguard"]["guard_status"] == "failed"
    assert result["finguard"]["guard_error"] == "guard-boom"
    assert result["finguard"]["verify_status"] == "skipped"
