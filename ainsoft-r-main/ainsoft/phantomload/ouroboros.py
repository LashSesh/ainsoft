"""Ouroboros quadrupole timing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class QuadrupoleState:
    """Represents the active quadrupole cell pair."""

    phase: int
    active_cells: Tuple[str, str]


class OuroborosQuadrupole:
    """Simulates a four-cell asynchronous breathing cycle."""

    def __init__(self, *, cells: List[str] | None = None) -> None:
        self.cells = cells or ["north", "east", "south", "west"]
        if len(self.cells) != 4:
            raise ValueError("OuroborosQuadrupole expects exactly four cells")
        self._phase = 0
        self._history: List[QuadrupoleState] = []

    def advance(self) -> QuadrupoleState:
        """Advance to the next phase and return the new state."""

        active = (self.cells[self._phase], self.cells[(self._phase + 2) % 4])
        state = QuadrupoleState(phase=self._phase, active_cells=active)
        self._history.append(state)
        self._phase = (self._phase + 1) % 4
        return state

    def reset(self) -> None:
        """Reset the quadrupole state history."""

        self._phase = 0
        self._history.clear()

    def current_state(self) -> QuadrupoleState:
        """Return the most recent state without advancing the cycle."""

        if self._history:
            return self._history[-1]
        return QuadrupoleState(phase=self._phase, active_cells=(self.cells[0], self.cells[2]))

    def history(self) -> List[QuadrupoleState]:
        """Return the collected quadrupole states."""

        return list(self._history)

    def summary(self) -> Dict[str, object]:
        """Return a serialisable summary of the quadrupole state."""

        state = self.current_state()
        return {
            "phase": state.phase,
            "active_cells": list(state.active_cells),
            "history_length": len(self._history),
        }
