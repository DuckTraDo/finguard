import json
from pathlib import Path

from finguard.fin_utils import normalize_sources


def test_source_trace_replays_are_stable():
    fixture_path = Path(__file__).parent / "fixtures" / "source_trace_replays.json"
    replays = json.loads(fixture_path.read_text(encoding="utf-8"))

    for replay in replays:
        sources = normalize_sources(messages=replay["messages"])

        assert isinstance(sources, list), replay["name"]
        assert len(sources) >= replay["expected_min_sources"], replay["name"]
        assert all(isinstance(source, dict) for source in sources), replay["name"]
        assert all("source_id" in source for source in sources), replay["name"]
        assert all("title" in source for source in sources), replay["name"]
        assert all("content" in source for source in sources), replay["name"]

        tool_names = {source.get("tool_name") for source in sources}
        for expected_tool_name in replay["expected_tool_names"]:
            assert expected_tool_name in tool_names, replay["name"]
