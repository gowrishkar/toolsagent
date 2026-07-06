from pathlib import Path

from agent_discipline import AgentDisciplineLayer, Evidence


def test_contract_blocks_finish_until_all_checks_have_evidence():
    layer = AgentDisciplineLayer()
    contract = layer.create_contract(
        goal="Build a GitHub-ready package",
        done_checks=["tests pass", "README exists", "example runs"],
    )

    layer.add_evidence(contract, "tests pass", output="4 passed")
    layer.add_evidence(contract, "README exists", path="README.md")
    result = layer.can_finish(contract)

    assert result.allowed is False
    assert result.missing == ["example runs"]
    assert "example runs" in result.report

    layer.add_evidence(contract, "example runs", output="printed priming data")
    result = layer.can_finish(contract)

    assert result.allowed is True
    assert result.missing == []


def test_detects_lazy_claims_without_evidence():
    layer = AgentDisciplineLayer()
    flags = layer.detect_laziness(
        message="Done. I created the project and it should work.",
        evidence=[],
        tool_calls_made=False,
    )

    assert "claimed_done_without_evidence" in flags
    assert "no_tool_calls" in flags
    assert "vague_success_language" in flags


def test_path_evidence_checks_file_existence(tmp_path):
    layer = AgentDisciplineLayer()
    contract = layer.create_contract(
        goal="Prepare package",
        done_checks=["README exists"],
    )
    readme = tmp_path / "README.md"
    readme.write_text("# Demo")

    layer.add_evidence(contract, "README exists", path=str(readme))
    result = layer.can_finish(contract)

    assert result.allowed is True
    assert contract.evidence["README exists"][0].exists is True


def test_mark_failed_evidence_keeps_contract_unfinished():
    layer = AgentDisciplineLayer()
    contract = layer.create_contract(
        goal="Run tests",
        done_checks=["tests pass"],
    )

    layer.add_evidence(contract, "tests pass", status="failed", output="1 failed")
    result = layer.can_finish(contract)

    assert result.allowed is False
    assert result.failed == ["tests pass"]
    assert "1 failed" in result.report


def test_next_action_prioritizes_missing_then_failed_checks():
    layer = AgentDisciplineLayer()
    contract = layer.create_contract(
        goal="Build thing",
        done_checks=["tests pass", "example runs"],
    )
    layer.add_evidence(contract, "tests pass", status="failed", output="ImportError")

    assert layer.next_action(contract) == "Fix failed check: tests pass"

    contract = layer.create_contract(
        goal="Build thing",
        done_checks=["tests pass", "example runs"],
    )
    assert layer.next_action(contract) == "Collect evidence for: tests pass"
