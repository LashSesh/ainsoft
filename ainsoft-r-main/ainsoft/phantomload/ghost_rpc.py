"""GhostRPC engine for synthetic phantomload traffic."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
import time
from typing import Dict, Iterable, List, Optional

from .proxy_manager import ProxyManager


@dataclass
class GhostRPCNode:
    """Represents a transient phantom RPC node."""

    node_id: str
    endpoint: str
    seed: str
    metadata: Dict[str, object] = field(default_factory=dict)
    active: bool = True
    last_latency: float = 0.0
    requests_sent: int = 0

    def snapshot(self) -> Dict[str, object]:
        """Return a serialisable view of the node state."""

        data = dict(self.metadata)
        data.update(
            {
                "id": self.node_id,
                "endpoint": self.endpoint,
                "seed": self.seed,
                "active": self.active,
                "last_latency": self.last_latency,
                "requests_sent": self.requests_sent,
            }
        )
        return data


@dataclass
class GhostRPCWave:
    """Active phantomload wave description."""

    mode: str
    pattern: str
    nodes: List[GhostRPCNode]
    endpoint: str
    started_at: float = field(default_factory=time.time)
    status: str = "running"
    metrics: Dict[str, object] = field(
        default_factory=lambda: {
            "requests": 0,
            "errors": 0,
            "avg_latency": 0.0,
        }
    )

    def update_metrics(self, latencies: Iterable[float]) -> None:
        """Update aggregate metrics with new latency values."""

        latencies = list(latencies)
        if not latencies:
            return
        self.metrics["requests"] += len(latencies)
        self.metrics["avg_latency"] = sum(latencies) / max(1, len(latencies))

    def snapshot(self) -> Dict[str, object]:
        """Return a serialisable representation of the wave."""

        return {
            "mode": self.mode,
            "pattern": self.pattern,
            "endpoint": self.endpoint,
            "started_at": self.started_at,
            "status": self.status,
            "metrics": dict(self.metrics),
            "nodes": [node.snapshot() for node in self.nodes],
        }


class GhostRPCManager:
    """Coordinates phantom RPC waves and synthesised traffic."""

    def __init__(self, proxy_manager: Optional[ProxyManager] = None) -> None:
        self.proxy_manager = proxy_manager or ProxyManager()
        self._wave: Optional[GhostRPCWave] = None
        self._last_tick: float = 0.0

    def start_wave(
        self,
        *,
        mode: str,
        pattern: str,
        nodes: List[GhostRPCNode],
        endpoint: str,
    ) -> GhostRPCWave:
        """Start a new phantomload wave."""

        wave = GhostRPCWave(mode=mode, pattern=pattern, nodes=nodes, endpoint=endpoint)
        self._wave = wave
        self._last_tick = time.time()
        return wave

    def stop_wave(self) -> None:
        """Stop the currently running wave."""

        if self._wave:
            self._wave.status = "stopped"
        self._wave = None

    def tick(self) -> Optional[Dict[str, object]]:
        """Simulate a single heartbeat worth of traffic."""

        if not self._wave:
            return None

        latencies: List[float] = []
        for node in self._wave.nodes:
            if not node.active:
                continue
            latency = random.uniform(0.01, 0.3)
            jitter = random.uniform(-0.005, 0.005)
            node.last_latency = max(0.0, latency + jitter)
            node.requests_sent += 1
            latencies.append(node.last_latency)

        self._wave.update_metrics(latencies)
        self._last_tick = time.time()
        return {
            "wave": self._wave.snapshot(),
            "proxy": self.proxy_manager.snapshot(),
            "timestamp": self._last_tick,
        }

    def status(self) -> Dict[str, object]:
        """Return the current wave status."""

        if not self._wave:
            return {"active": False, "wave": None, "proxy": self.proxy_manager.snapshot()}
        return {
            "active": True,
            "wave": self._wave.snapshot(),
            "proxy": self.proxy_manager.snapshot(),
        }

    def active_wave(self) -> Optional[GhostRPCWave]:
        """Return the active wave if available."""

        return self._wave
