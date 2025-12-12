"""Impulse construction and execution."""

from __future__ import annotations

from typing import Dict, Optional
import socket

from ainsoft.core.network import ProxyConfig, create_socket_with_optional_proxy


class Impulse:
    """Construct and fire impulses towards a target."""

    def __init__(self) -> None:
        self.last_vector: Optional[bytes] = None

    def construct(self, state: Dict) -> bytes:
        """Build an impulse vector from the provided *state*."""

        data = str(state).encode("utf-8")
        self.last_vector = data
        return data

    def fire(
        self,
        vector: bytes,
        target: str,
        port: int = 80,
        *,
        proxy_config: Optional[ProxyConfig] = None,
    ) -> bool:
        """Send the impulse via UDP to the target system.

        The socket honours the optional SOCKS5 proxy configuration.
        """

        try:
            with create_socket_with_optional_proxy(
                proxy_config,
                family=socket.AF_INET,
                type=socket.SOCK_DGRAM,
            ) as sock:
                sock.sendto(vector, (target, port))
            return True
        except OSError as exc:  # pragma: no cover - depends on environment
            print(f"Impulse send error: {exc}")
            return False

