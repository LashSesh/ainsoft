"""Structured network probe emitter."""

from __future__ import annotations

import random
import socket
import time
from typing import Dict, Optional

from ainsoft.core.network import ProxyConfig, create_socket_with_optional_proxy


def emit_probe_pattern(
    target: str,
    port: int = 8080,
    proxy_config: Optional[ProxyConfig] = None,
) -> Dict:
    """Send a randomised UDP probe and return metadata about the attempt.

    The underlying socket honours the optional SOCKS5 proxy configuration.
    """

    probe_type = random.choice(["A", "B", "C", "D"])
    payload = f"PROBE-{probe_type}-{time.time()}".encode("utf-8")
    timestamp = time.time()
    try:
        with create_socket_with_optional_proxy(
            proxy_config,
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
        ) as sock:
            sock.sendto(payload, (target, port))
        return {"status": "sent", "pattern": probe_type, "timestamp": timestamp}
    except OSError as exc:  # pragma: no cover - depends on network availability
        return {"status": "error", "error": str(exc), "timestamp": timestamp}

