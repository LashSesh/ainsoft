"""UDP response observer for probe replies."""

from __future__ import annotations

import socket
import time
from typing import Dict, List, Optional

from ainsoft.core.network import ProxyConfig, create_socket_with_optional_proxy


def collect_responses(
    port: int = 8080,
    listen_time: float = 0.25,
    proxy_config: Optional[ProxyConfig] = None,
) -> List[Dict]:
    """Listen for UDP responses for ``listen_time`` seconds.

    Local sockets bind directly; proxy usage is skipped because SOCKS5 does not
    relay inbound UDP binds in this context, but the signature stays consistent.
    """

    responses: List[Dict] = []
    with create_socket_with_optional_proxy(
        proxy_config,
        family=socket.AF_INET,
        type=socket.SOCK_DGRAM,
        allow_proxy=False,
    ) as sock:
        sock.setblocking(False)
        sock.bind(("", port))
        start = time.time()
        while time.time() - start < listen_time:
            try:
                data, addr = sock.recvfrom(1024)
            except BlockingIOError:
                time.sleep(0.01)
                continue
            latency = time.time() - start
            responses.append(
                {
                    "latency": latency,
                    "payload": data.decode("utf-8", errors="replace"),
                    "address": addr,
                    "timestamp": time.time(),
                }
            )
    return responses

