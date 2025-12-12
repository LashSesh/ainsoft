"""Network dispatcher utilities with optional SOCKS5 proxy support."""

from __future__ import annotations

import socket
from typing import Any, Mapping, Optional, Tuple

from ainsoft.core.network import ProxyConfig, create_socket_with_optional_proxy

DEFAULT_TARGET: Tuple[str, int] = ("127.0.0.1", 8080)


def _resolve_target(payload: Any) -> Tuple[str, int]:
    if isinstance(payload, Mapping):
        target = payload.get("target") or payload.get("destination")
        if isinstance(target, (list, tuple)) and len(target) == 2:
            return str(target[0]), int(target[1])
        host = payload.get("host") or payload.get("url") or DEFAULT_TARGET[0]
        port = int(payload.get("port", DEFAULT_TARGET[1]))
        return host, port
    return DEFAULT_TARGET


def _resolve_bytes(payload: Any) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    if isinstance(payload, Mapping):
        body = payload.get("body")
        if isinstance(body, (bytes, str)):
            return body.encode("utf-8") if isinstance(body, str) else body
    return str(payload).encode("utf-8")


def network_dispatcher(payload: Any, proxy_cfg: Optional[ProxyConfig] = None) -> Mapping[str, Any]:
    """Dispatch *payload* over TCP, optionally via a SOCKS5 proxy."""

    host, port = _resolve_target(payload)
    data = _resolve_bytes(payload)

    sock = create_socket_with_optional_proxy(
        proxy_cfg,
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
    )
    try:
        sock.settimeout(1.0)
        sock.connect((host, port))
        sock.sendall(data)
        return {"status": "sent", "target": (host, port), "bytes": len(data)}
    except OSError as exc:
        return {"status": "error", "target": (host, port), "error": str(exc)}
    finally:
        sock.close()


__all__ = ["network_dispatcher"]
