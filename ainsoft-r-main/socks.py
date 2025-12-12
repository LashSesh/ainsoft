"""Lightweight stub to provide the PySocks interface in offline test environments."""

from __future__ import annotations

import socket


SOCKS5 = 2


class ProxyNotAvailableError(RuntimeError):
    """Raised when proxy functionality is requested without PySocks installed."""


class socksocket(socket.socket):
    """Fallback socket mimicking :class:`PySocks.socksocket` when unavailable."""

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        super().__init__(family, type, proto, _sock)
        self._proxy_config = None

    def set_proxy(self, proxy_type, addr, port, username=None, password=None):  # noqa: D401
        """Store proxy parameters and signal the lack of PySocks implementation."""

        self._proxy_config = {
            "proxy_type": proxy_type,
            "addr": addr,
            "port": port,
            "username": username,
            "password": password,
        }
        raise ProxyNotAvailableError(
            "SOCKS proxy functionality requires the PySocks package."
        )

