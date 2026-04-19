from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from run_agent import AIAgent


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


def _mock_tool_call(name: str = "web_search", arguments: str = "{}", call_id: str = "call_1"):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


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


def test_compliance_query_is_blocked_before_llm(agent):
    with (
        patch.object(agent, "_interruptible_api_call") as mock_api_call,
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("Should I buy AAPL right now?")

    mock_api_call.assert_not_called()
    assert result["api_calls"] == 0
    assert result["finguard"]["expected_behavior"] == "refuse_with_disclaimer"
    assert "Disclaimer:" in result["final_response"]


def test_financial_query_runs_guard_to_verify_smoke(agent):
    tool_call = _mock_tool_call(
        name="web_search",
        arguments='{"url":"https://example.com/aapl-2023"}',
        call_id="call_1",
    )
    first_response = _mock_response(content="", finish_reason="tool_calls", tool_calls=[tool_call])
    second_response = _mock_response(content="AAPL revenue was 100 in 2023.", finish_reason="stop")
    agent.client.chat.completions.create.side_effect = [first_response, second_response]

    with (
        patch("run_agent.handle_function_call", return_value="AAPL revenue was 100 in 2023. https://example.com/aapl-2023"),
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("What was AAPL revenue in 2023?")

    assert result["completed"] is True
    assert result["finguard"]["query_type"] == "factual"
    assert result["finguard"]["verify_status"] == "ok"
    assert result["finguard"]["source_count"] == 1
    assert result["finguard"]["verified_number_count"] == 2
    assert result["sources"]
    assert result["sources"][0]["tool_name"] == "web_search"
    assert "Sources:" in result["final_response"]


def test_augmented_query_returns_original_user_message_in_history(agent):
    response = _mock_response(content="Investors should consider valuation and cash flow.", finish_reason="stop")
    agent.client.chat.completions.create.return_value = response

    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("Explain the risks of buying AAPL today.")

    user_messages = [msg for msg in result["messages"] if msg.get("role") == "user"]
    assert user_messages
    assert user_messages[0]["content"] == "Explain the risks of buying AAPL today."
    assert result["finguard"]["query_augmented"] is True
    assert result["finguard"]["expected_behavior"] == "answer_with_disclaimer"
    assert result["finguard"]["verify_status"] == "ok"
    assert "Disclaimer:" in result["final_response"]
