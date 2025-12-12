"""Agent state container for orchestrator workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentState:
    """Light-weight structure capturing lifecycle artefacts."""

    target: str
    port: int
    history: List[Dict[str, Any]] = field(default_factory=list)

    def record(self, event: Dict[str, Any]) -> None:
        self.history.append(event)

