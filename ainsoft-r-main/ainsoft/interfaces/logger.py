"""Logging utilities for AinSOFT."""

from __future__ import annotations

import logging

logger = logging.getLogger("ainsoft")
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def log_event(event: str) -> None:
    """Log *event* using the configured logger."""

    logger.info(event)

