"""Proxy configuration utilities for the Phantomload expansion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ProxyManager:
    """Tracks SOCKS5/HTTP proxy configuration for phantom traffic."""

    config: Dict[str, Optional[str | int | bool]] = field(
        default_factory=lambda: {
            "enabled": False,
            "type": "socks5",
            "host": None,
            "port": None,
            "username": None,
            "password": None,
        }
    )

    def configure(self, payload: Dict[str, Optional[str | int | bool]]) -> Dict[str, Optional[str | int | bool]]:
        """Merge a new configuration payload into the current settings."""

        self.config.update(payload)
        return self.snapshot()

    def snapshot(self) -> Dict[str, Optional[str | int | bool]]:
        """Return a copy of the active proxy configuration."""

        return dict(self.config)

    def is_enabled(self) -> bool:
        """Return ``True`` when proxy routing should be applied."""

        return bool(self.config.get("enabled"))
