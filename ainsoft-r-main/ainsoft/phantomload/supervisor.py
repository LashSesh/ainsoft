"""Supervisor panel helpers for the Phantomload expansion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PhantomloadSupervisor:
    """Maintain tunable runtime parameters for phantomload control."""

    parameters: Dict[str, object] = field(default_factory=dict)

    def configure(self, defaults: Dict[str, object]) -> None:
        """Initialise the supervisor with default parameters."""

        self.parameters.update(defaults)

    def get_params(self) -> Dict[str, object]:
        """Return a copy of the current parameters."""

        return dict(self.parameters)

    def set_param(self, name: str, value: object) -> Dict[str, object]:
        """Set a parameter and return the updated dictionary."""

        self.parameters[name] = value
        return self.get_params()

    def get_param(self, name: str, default: Optional[object] = None) -> object:
        """Return a single parameter value."""

        return self.parameters.get(name, default)
