"""Interface layer for AinSOFT (CLI, API, GUI)."""

from .gui import run  # noqa: F401  # Convenience re-export for launchers
from .resonance_gui import run as run_resonance  # noqa: F401

__all__ = ["run", "run_resonance"]
