import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.prompt_builder import build_skills_system_prompt, clear_skills_system_prompt_cache
from agent.skill_utils import parse_frontmatter
from run_agent import AIAgent
from tools.skills_sync import _discover_bundled_skills
from tools.skills_tool import skill_view

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_SKILLS_DIR = REPO_ROOT / "skills"
FINANCE_CATEGORY_DIR = BUNDLED_SKILLS_DIR / "finance"
FIN_SOURCE_CITATION_DIR = FINANCE_CATEGORY_DIR / "fin-source-citation"
FIN_SOURCE_CITATION_MD = FIN_SOURCE_CITATION_DIR / "SKILL.md"


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
def installed_skill_home(tmp_path):
    hermes_home = tmp_path / ".hermes"
    skill_dest_dir = hermes_home / "skills" / "finance" / "fin-source-citation"
    skill_dest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIN_SOURCE_CITATION_DIR, skill_dest_dir)
    shutil.copy2(FINANCE_CATEGORY_DIR / "DESCRIPTION.md", skill_dest_dir.parent / "DESCRIPTION.md")
    return hermes_home


@pytest.fixture()
def empty_skill_home(tmp_path):
    hermes_home = tmp_path / ".hermes-empty"
    (hermes_home / "skills").mkdir(parents=True, exist_ok=True)
    return hermes_home


def _run_finance_query_and_capture_system_message(hermes_home: Path) -> tuple[str, dict]:
    clear_skills_system_prompt_cache(clear_snapshot=True)
    with (
        patch.dict(os.environ, {"HERMES_HOME": str(hermes_home)}, clear=False),
        patch(
            "run_agent.get_tool_definitions",
            return_value=_make_tool_defs("web_search", "skills_list", "skill_view", "skill_manage"),
        ),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch(
            "run_agent.get_toolset_for_tool",
            side_effect={
                "web_search": "web",
                "skills_list": "skills",
                "skill_view": "skills",
                "skill_manage": "skills",
            }.get,
            create=True,
        ),
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
        agent.client.chat.completions.create.return_value = _mock_response(
            content="AAPL revenue was 100 in 2023.",
            finish_reason="stop",
        )
        agent._use_prompt_caching = False
        agent.tool_delay = 0
        agent.compression_enabled = False
        agent.save_trajectories = False

        with (
            patch.object(agent, "_persist_session"),
            patch.object(agent, "_save_trajectory"),
            patch.object(agent, "_cleanup_task_resources"),
        ):
            result = agent.run_conversation("What was AAPL revenue in 2023?")

        sent_messages = agent.client.chat.completions.create.call_args.kwargs["messages"]
        system_message = sent_messages[0]

    assert system_message["role"] == "system"
    return str(system_message["content"]), result


def test_fin_source_citation_template_is_discoverable_and_viewable(installed_skill_home):
    assert FIN_SOURCE_CITATION_MD.exists()

    raw_content = FIN_SOURCE_CITATION_MD.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw_content)
    assert frontmatter["name"] == "fin-source-citation"
    assert "Conservative citation workflow" in frontmatter["description"]
    assert "Never invent a filing" in body

    bundled_names = {name for name, _path in _discover_bundled_skills(BUNDLED_SKILLS_DIR)}
    assert "fin-source-citation" in bundled_names

    clear_skills_system_prompt_cache(clear_snapshot=True)
    with (
        patch.dict(os.environ, {"HERMES_HOME": str(installed_skill_home)}, clear=False),
        patch("tools.skills_tool.SKILLS_DIR", installed_skill_home / "skills"),
    ):
        skills_prompt = build_skills_system_prompt(
            available_tools={"web_search", "skills_list", "skill_view", "skill_manage"},
            available_toolsets={"web", "skills"},
        )
        viewed = json.loads(skill_view("fin-source-citation"))

    assert "finance:" in skills_prompt
    assert "fin-source-citation" in skills_prompt
    assert "Conservative citation workflow" in skills_prompt
    assert viewed["success"] is True
    assert viewed["name"] == "fin-source-citation"
    assert "Never invent a filing" in viewed["content"]


def test_fin_source_citation_does_not_break_run_conversation(installed_skill_home):
    prompt, result = _run_finance_query_and_capture_system_message(installed_skill_home)
    assert "fin-source-citation" in prompt
    assert "finance:" in prompt
    assert result["completed"] is True
    assert result["final_response"]


def test_fin_source_citation_changes_system_message_sent_to_model(
    empty_skill_home,
    installed_skill_home,
):
    prompt_without_skill, result_without_skill = _run_finance_query_and_capture_system_message(
        empty_skill_home
    )
    prompt_with_skill, result_with_skill = _run_finance_query_and_capture_system_message(
        installed_skill_home
    )

    assert "fin-source-citation" not in prompt_without_skill
    assert "Conservative citation workflow" not in prompt_without_skill
    assert "finance:" not in prompt_without_skill

    assert "fin-source-citation" in prompt_with_skill
    assert "Conservative citation workflow" in prompt_with_skill
    assert "finance:" in prompt_with_skill
    assert prompt_with_skill != prompt_without_skill

    assert result_without_skill["completed"] is True
    assert result_with_skill["completed"] is True
