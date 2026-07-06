"""ToolsAgent — how agents should behave (Submind)."""

from .agent_discipline import (
    AgentDisciplineLayer,
    CompletionContract,
    Evidence,
    FinishResult,
)
from .subconscious_layer import SubconsciousLayer

__all__ = [
    "AgentDisciplineLayer",
    "CompletionContract",
    "Evidence",
    "FinishResult",
    "SubconsciousLayer",
]