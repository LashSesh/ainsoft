"""Helper utilities for loading the Phantomload expansion configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).with_name("phantomload.yaml")


def load_phantomload_config(path: str | Path | None = None) -> Dict[str, Any]:
    """Load the Phantomload expansion configuration file."""

    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


__all__ = ["load_phantomload_config", "DEFAULT_CONFIG_PATH"]
