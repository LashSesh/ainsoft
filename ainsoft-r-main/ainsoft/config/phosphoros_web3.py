"""Helper utilities for loading the Phosphoros Web3 configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).with_name("phosphoros_web3.yaml")


def load_phosphoros_web3_config(path: str | Path | None = None) -> Dict[str, Any]:
    """Load the default Phosphoros Web3 configuration file."""

    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


__all__ = ["load_phosphoros_web3_config", "DEFAULT_CONFIG_PATH"]

