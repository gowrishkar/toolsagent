import asyncio
import json
from pathlib import Path

from subconscious_layer import SubconsciousLayer


def run(coro):
    return asyncio.run(coro)


def test_reflect_stores_successful_run_and_top_actions(tmp_path):
    store = tmp_path / "memory.json"
    procedures = tmp_path / "procedures.md"
    layer = SubconsciousLayer(store_path=store, procedural_path=procedures)

    run(layer.reflect([
        {"action": "search_web", "result": "found info"},
        {"action": "summarize", "result": "done"},
    ], success=True))
    run(layer.reflect([
        {"action": "search_web", "result": "found more"},
        {"action": "write_file", "result": "saved"},
    ], success=True))

    data = json.loads(store.read_text())
    assert len(data["patterns"]) == 2
    assert data["procedures"]["frequent_actions"][0] == ["search_web", 2]
    assert procedures.exists()
    assert "search_web" in procedures.read_text()


def test_never_overwrites_existing_procedural_file_without_managed_block(tmp_path):
    store = tmp_path / "memory.json"
    procedures = tmp_path / "soul.md"
    procedures.write_text("# Existing Soul\n\nKeep this line.\n")
    layer = SubconsciousLayer(store_path=store, procedural_path=procedures)

    run(layer.reflect([{"action": "test_action", "result": "ok"}], success=True))

    text = procedures.read_text()
    assert "# Existing Soul" in text
    assert "Keep this line." in text
    assert "BEGIN SUBCONSCIOUS LAYER" in text
    assert "test_action" in text


def test_prime_returns_implicit_habits_recent_patterns_and_recommendations(tmp_path):
    layer = SubconsciousLayer(
        store_path=tmp_path / "memory.json",
        procedural_path=tmp_path / "procedures.md",
        max_patterns=5,
    )
    for i in range(4):
        run(layer.reflect([
            {"action": "research", "result": f"result {i}"},
            {"action": "verify", "result": "checked"},
        ], success=i != 0))

    prime = layer.prime("Need to answer user safely")

    assert prime["implicit_habits"][0] == "research"
    assert len(prime["recent_patterns"]) == 3
    assert any("Verify" in rec for rec in prime["recommendations"])


def test_memory_is_pruned_to_max_patterns(tmp_path):
    layer = SubconsciousLayer(
        store_path=tmp_path / "memory.json",
        procedural_path=tmp_path / "procedures.md",
        max_patterns=3,
    )

    for i in range(6):
        run(layer.reflect([{"action": f"action_{i}", "result": "ok"}], success=True))

    data = json.loads((tmp_path / "memory.json").read_text())
    assert len(data["patterns"]) == 3
    assert data["patterns"][0]["key_actions"] == ["action_3"]
