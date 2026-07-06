"""Minimal Submind demo."""

from agent_discipline import AgentDisciplineLayer


def main() -> None:
    layer = AgentDisciplineLayer()
    contract = layer.create_contract(
        goal="Build a GitHub-ready Python package",
        done_checks=["README exists", "tests pass", "example runs"],
    )

    layer.add_evidence(contract, "README exists", path="README.md")
    layer.add_evidence(contract, "tests pass", output="9 passed in 0.10s")

    result = layer.can_finish(contract)
    print(result.report)
    print("Next action:", layer.next_action(contract))

    layer.add_evidence(contract, "example runs", output="demo printed expected report")
    result = layer.can_finish(contract)
    print("\nAfter adding example evidence:")
    print(result.report)


if __name__ == "__main__":
    main()
