import json
from contextlib import ExitStack
from pathlib import Path
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


def _run_snapshot_case(agent: AIAgent, case: dict) -> dict:
    if case["mode"] == "single_response":
        agent.client.chat.completions.create.side_effect = None
        agent.client.chat.completions.create.return_value = _mock_response(
            content=case["model_response"],
            finish_reason="stop",
        )
        patches = (
            patch.object(agent, "_persist_session"),
            patch.object(agent, "_save_trajectory"),
            patch.object(agent, "_cleanup_task_resources"),
        )
    elif case["mode"] == "tool_then_response":
        first_response = _mock_response(
            content="",
            finish_reason="tool_calls",
            tool_calls=[
                _mock_tool_call(
                    name=case["tool_name"],
                    arguments=case["tool_arguments"],
                    call_id=case["tool_call_id"],
                )
            ],
        )
        second_response = _mock_response(
            content=case["model_response"],
            finish_reason="stop",
        )
        agent.client.chat.completions.create.side_effect = [first_response, second_response]
        patches = (
            patch("run_agent.handle_function_call", return_value=case["tool_output"]),
            patch.object(agent, "_persist_session"),
            patch.object(agent, "_save_trajectory"),
            patch.object(agent, "_cleanup_task_resources"),
        )
    else:
        agent.client.chat.completions.create.side_effect = None
        patches = (
            patch.object(agent, "_persist_session"),
            patch.object(agent, "_save_trajectory"),
            patch.object(agent, "_cleanup_task_resources"),
        )

    with ExitStack() as stack:
        for active_patch in patches:
            stack.enter_context(active_patch)
        result = agent.run_conversation(case["query"])

    final_response = result["final_response"]
    return {
        "response_contains": list(case["expected"]["response_contains"]),
        "matched_response_contains": [
            fragment for fragment in case["expected"]["response_contains"] if fragment in final_response
        ],
        "disclaimer_present": "Disclaimer:" in final_response,
        "sources_present": "Sources:" in final_response,
        "verification_note_present": "Verification note:" in final_response,
        "finguard": {
            "passed": result["finguard"]["passed"],
            "query_type": result["finguard"]["query_type"],
            "expected_behavior": result["finguard"]["expected_behavior"],
            "query_augmented": result["finguard"]["query_augmented"],
            "source_count": result["finguard"]["source_count"],
            "verify_status": result["finguard"]["verify_status"],
        },
    }


def test_finguard_response_snapshots(agent):
    fixture_path = Path(__file__).parent / "fixtures" / "response_snapshots.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    for case in cases:
        actual = _run_snapshot_case(agent, case)
        assert actual["matched_response_contains"] == case["expected"]["response_contains"]
        assert actual["disclaimer_present"] == case["expected"]["disclaimer_present"]
        assert actual["sources_present"] == case["expected"]["sources_present"]
        assert (
            actual["verification_note_present"] == case["expected"]["verification_note_present"]
        )
        assert actual["finguard"] == case["expected"]["finguard"]
