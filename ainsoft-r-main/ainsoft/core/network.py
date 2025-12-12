"""Utility helpers for creating sockets with optional SOCKS5 proxy support."""

from __future__ import annotations

from typing import Mapping, Optional

import socket

import socks


ProxyConfig = Optional[Mapping[str, object]]


def _is_proxy_enabled(proxy_cfg: ProxyConfig) -> bool:
    """Check whether the supplied proxy configuration is active."""

    if not proxy_cfg:
        return False
    if not proxy_cfg.get("enabled"):
        return False
    host = proxy_cfg.get("host")
    port = proxy_cfg.get("port")
    return bool(host and port)


def create_socket_with_optional_proxy(
    proxy_cfg: ProxyConfig,
    *,
    family: int = socket.AF_INET,
    type: int = socket.SOCK_STREAM,
    proto: int = 0,
    allow_proxy: bool = True,
):
    """Create a socket that honours optional SOCKS5 proxy configuration.

    The proxy configuration follows the structure used in the project-wide
    configuration schema. If ``allow_proxy`` is False a standard socket is
    returned regardless of the configuration (useful for local binds).
    """

    if allow_proxy and _is_proxy_enabled(proxy_cfg):
        sock = socks.socksocket(family, type, proto)
        sock.set_proxy(
            socks.SOCKS5,
            proxy_cfg["host"],
            proxy_cfg["port"],
            username=proxy_cfg.get("username"),
            password=proxy_cfg.get("password"),
        )
        return sock
    return socket.socket(family, type, proto)


__all__ = ["ProxyConfig", "create_socket_with_optional_proxy"]

