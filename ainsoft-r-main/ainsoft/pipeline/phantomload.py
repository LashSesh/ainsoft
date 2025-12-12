"""Phantomload & GhostRPC expansion pack utilities.

This module follows the "AinSOFT Phantomload & GhostRPC" blueprint by providing
lightweight, dependency-free primitives for synthetic RPC traffic simulation,
quadrupole timing cycles and mesh/heatmap export.  The implementation is kept
pure Python to stay fully testable while still reflecting the semantics of the
specification:

* :class:`GhostRPCEngine` manages ephemeral phantom nodes and creates
  synthetic traffic waves.
* :class:`OuroborosQuadrupole` implements the four-channel asynchronous
  breathing pattern used to drive the engine.
* :class:`PhantomloadKernel` orchestrates the blueprint components, integrates
  with the existing seed/mutation utilities from the Web3 suite and exposes
  mesh snapshots for Unity or external dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import itertools
import random
import threading
import time
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

import numpy as np

from .web3suite import (
    ExportModule,
    MetaMemoryCore,
    MutationEngine,
    ReverbRing,
    ScorpioBridge,
    SeedClusterEngine,
    SeedDNAEngine,
    SupervisorInterface,
)


@dataclass
class PhantomNode:
    """Represents a synthetic RPC/traffic node inside the phantom mesh."""

    identifier: str
    geometry: np.ndarray
    seed_phrase: str
    active: bool = True
    cluster: Optional[int] = None
    weight: float = 0.0
    last_event: float = field(default_factory=time.time)
    metadata: MutableMapping[str, float] = field(default_factory=dict)

    def position3d(self) -> List[float]:
        """Return a 3D projection of the 5D geometry for visualisation."""

        vector = np.asarray(self.geometry, dtype=float)
        if vector.size < 3:
            vector = np.pad(vector, (0, 3 - vector.size))
        return vector[:3].tolist()


class ProxyManager:
    """Simple proxy rotation helper for phantom traffic."""

    def __init__(self) -> None:
        self._proxies: List[str] = []
        self._mode: str = "round_robin"
        self._index: int = 0
        self._lock = threading.Lock()

    def configure(self, proxies: Sequence[str], mode: str = "round_robin") -> None:
        """Configure the proxy list and rotation mode."""

        with self._lock:
            self._proxies = list(proxies)
            self._mode = mode
            self._index = 0

    def acquire(self) -> Optional[str]:
        """Return the proxy to be used for the next phantom request."""

        with self._lock:
            if not self._proxies:
                return None
            if self._mode == "random":
                return random.choice(self._proxies)
            proxy = self._proxies[self._index % len(self._proxies)]
            self._index += 1
            return proxy

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def proxies(self) -> List[str]:
        with self._lock:
            return list(self._proxies)


class OuroborosQuadrupole:
    """Generates four-phase activation patterns for the GhostRPC engine."""

    def __init__(self) -> None:
        self._cycle = itertools.cycle(((0, 2), (1, 3), (0, 1), (2, 3)))
        self._tick = 0

    def advance(self) -> Tuple[int, int]:
        """Return the next pair of active channels."""

        self._tick += 1
        return next(self._cycle)

    def reset(self) -> None:
        """Reset the internal cycle state."""

        self._cycle = itertools.cycle(((0, 2), (1, 3), (0, 1), (2, 3)))
        self._tick = 0


class GhostRPCEngine:
    """Maintains phantom nodes and simulates traffic waves."""

    def __init__(
        self,
        rpc_targets: Optional[Sequence[str]] = None,
        *,
        idle_timeout: float = 1.5,
        decay: float = 0.9,
        proxy_manager: Optional[ProxyManager] = None,
    ) -> None:
        self.rpc_targets = list(rpc_targets or ["rpc://localhost"])
        self.idle_timeout = idle_timeout
        self.decay = decay
        self.proxy_manager = proxy_manager or ProxyManager()
        self._nodes: Dict[str, PhantomNode] = {}
        self._events: List[MutableMapping[str, object]] = []
        self._lock = threading.Lock()
        self._random = random.Random()

    # ------------------------------------------------------------------
    # Node management helpers
    # ------------------------------------------------------------------
    def add_node(self, node: PhantomNode) -> None:
        """Register a phantom node with the engine."""

        with self._lock:
            self._nodes[node.identifier] = node

    def clear(self) -> None:
        """Remove all phantom nodes and events."""

        with self._lock:
            self._nodes.clear()
            self._events.clear()

    def iter_nodes(self) -> List[PhantomNode]:
        """Return a snapshot copy of the currently active nodes."""

        with self._lock:
            clones: List[PhantomNode] = []
            for node in self._nodes.values():
                clones.append(
                    PhantomNode(
                        identifier=node.identifier,
                        geometry=np.array(node.geometry, dtype=float),
                        seed_phrase=node.seed_phrase,
                        active=node.active,
                        cluster=node.cluster,
                        weight=node.weight,
                        last_event=node.last_event,
                        metadata=dict(node.metadata),
                    )
                )
            return clones

    def assign_clusters(self, labels: Sequence[int]) -> None:
        """Persist the computed cluster labels back into the nodes."""

        with self._lock:
            for node, label in zip(self._nodes.values(), labels):
                node.cluster = int(label)

    # ------------------------------------------------------------------
    # Simulation step
    # ------------------------------------------------------------------
    def tick(self, active_channels: Sequence[int]) -> Optional[MutableMapping[str, object]]:
        """Simulate one heartbeat worth of phantom traffic."""

        with self._lock:
            if not self._nodes:
                return None

            now = time.time()
            node_ids = list(self._nodes.keys())
            active_nodes: List[str] = []
            for channel in active_channels:
                if not node_ids:
                    break
                node_id = self._random.choice(node_ids)
                node = self._nodes[node_id]
                node.weight = min(1.0, node.weight + 0.18)
                node.last_event = now
                node.metadata["channel"] = float(channel)
                active_nodes.append(node_id)

            retired: List[str] = []
            for node_id, node in list(self._nodes.items()):
                if node_id not in active_nodes:
                    node.weight = max(0.0, node.weight * self.decay)
                if now - node.last_event > self.idle_timeout:
                    retired.append(node_id)
                    del self._nodes[node_id]

            proxy = self.proxy_manager.acquire()
            target = self._random.choice(self.rpc_targets)
            event = {
                "timestamp": now,
                "channels": list(active_channels),
                "active_nodes": active_nodes,
                "retired_nodes": retired,
                "rpc_target": target,
                "proxy": proxy,
                "node_count": len(self._nodes),
            }
            self._events.append(event)
            return event

    def status(self) -> MutableMapping[str, object]:
        """Return a summary of the current phantomload state."""

        with self._lock:
            return {
                "nodes": len(self._nodes),
                "events": len(self._events),
                "last_event": self._events[-1]["timestamp"] if self._events else None,
                "targets": list(self.rpc_targets),
            }


@dataclass
class PhantomloadKernel:
    """High-level orchestrator for the Phantomload expansion."""

    ghost_rpc: GhostRPCEngine = field(default_factory=GhostRPCEngine)
    bridge: ScorpioBridge = field(default_factory=ScorpioBridge)
    quadrupole: OuroborosQuadrupole = field(default_factory=OuroborosQuadrupole)
    dna_engine: SeedDNAEngine = field(default_factory=SeedDNAEngine)
    mutation_engine: MutationEngine = field(init=False)
    cluster_engine: SeedClusterEngine = field(default_factory=lambda: SeedClusterEngine(n_clusters=4))
    supervisor: SupervisorInterface = field(default_factory=SupervisorInterface)
    meta_memory: MetaMemoryCore = field(default_factory=lambda: MetaMemoryCore(max_history=256))
    export: ExportModule = field(default_factory=ExportModule)
    reverb: ReverbRing = field(default_factory=ReverbRing)
    proxy_manager: ProxyManager = field(default_factory=ProxyManager)
    _autostart: bool = True
    _running: bool = False
    _mode: str = "idle"
    _mesh_cache: MutableMapping[str, object] = field(default_factory=dict)
    _bridge_registered: bool = False
    _max_edges_per_cluster: int = 4

    def __post_init__(self) -> None:
        self.mutation_engine = MutationEngine(self.dna_engine)
        self.ghost_rpc.proxy_manager = self.proxy_manager

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_config(
        cls,
        config: MutableMapping[str, object],
        *,
        export_dir: str | Path | None = None,
    ) -> "PhantomloadKernel":
        """Instantiate a kernel from the YAML/Dict configuration."""

        phantom_cfg = config.get("phantomload", {}) if isinstance(config, dict) else {}
        heartbeat = float(phantom_cfg.get("heartbeat", 0.017))
        quadrupole_mode = bool(phantom_cfg.get("quadrupole_mode", True))
        idle_timeout = float(phantom_cfg.get("idle_timeout", 1.5))
        decay = float(phantom_cfg.get("mesh", {}).get("decay", 0.9))
        max_edges = int(phantom_cfg.get("mesh", {}).get("max_edges_per_cluster", 4))
        proxies = phantom_cfg.get("proxy", {}).get("proxy_list", [])
        proxy_mode = phantom_cfg.get("proxy", {}).get("mode", "round_robin")
        autostart = bool(phantom_cfg.get("bridge", {}).get("autostart", True))

        kernel = cls(
            ghost_rpc=GhostRPCEngine(idle_timeout=idle_timeout, decay=decay),
            bridge=ScorpioBridge(tick_interval=heartbeat),
        )
        kernel.proxy_manager.configure(proxies, mode=proxy_mode)
        kernel._autostart = autostart
        kernel._max_edges_per_cluster = max_edges
        if export_dir is not None:
            kernel.export = ExportModule(Path(export_dir))

        if not quadrupole_mode:
            # allow deterministic single-channel runs by fixing the cycle
            kernel.quadrupole = OuroborosQuadrupole()
            kernel.quadrupole._cycle = itertools.cycle(((0, 0),))  # type: ignore[attr-defined]
        return kernel

    def configure_proxy(self, proxies: Sequence[str], mode: str = "round_robin") -> None:
        """Update the proxy rotation settings."""

        self.proxy_manager.configure(proxies, mode=mode)

    # ------------------------------------------------------------------
    # Simulation lifecycle
    # ------------------------------------------------------------------
    def trigger(
        self,
        *,
        mode: str,
        nodes: int,
        mutate: bool = True,
        autostart: Optional[bool] = None,
    ) -> MutableMapping[str, object]:
        """Spawn phantom nodes and optionally start the heartbeat."""

        self.stop(clear_nodes=True)
        self._mode = mode
        self._running = True
        base_phrase = f"{mode}-{int(time.time()*1000)}"
        for index in range(max(1, nodes)):
            phrase = f"{base_phrase}-{index}"
            geometry = self.dna_engine.encode(phrase)
            if mutate:
                mutant = self.mutation_engine.generate_mutant(phrase)
                geometry = np.asarray(mutant[:5], dtype=float)
            node = PhantomNode(identifier=f"node-{index}", geometry=geometry, seed_phrase=phrase)
            self.ghost_rpc.add_node(node)
        if not self._bridge_registered:
            self.bridge.register_callback(self.tick)
            self._bridge_registered = True
        should_autostart = self._autostart if autostart is None else autostart
        if should_autostart:
            self.bridge.start()
        return self.status()

    def tick(self) -> None:
        """Execute one quadrupole heartbeat."""

        if not self._running:
            return
        channels = self.quadrupole.advance()
        event = self.ghost_rpc.tick(channels)
        if event is None:
            return
        activity = {
            "tick_time": event["timestamp"],
            "mode": self._mode,
            "active": len(event["active_nodes"]),
            "nodes": event.get("node_count", 0),
        }
        self.supervisor.update(activity)
        self.meta_memory.store(activity)
        self.reverb.log(activity)
        self._mesh_cache = self._build_mesh_snapshot()

    def stop(self, *, clear_nodes: bool = True) -> None:
        """Stop the heartbeat and optionally clear phantom nodes."""

        self.bridge.stop()
        self._running = False
        self.quadrupole.reset()
        if clear_nodes:
            self.ghost_rpc.clear()
        self._mesh_cache = {}

    # ------------------------------------------------------------------
    # Reporting utilities
    # ------------------------------------------------------------------
    def status(self) -> MutableMapping[str, object]:
        """Return a combined status view of the kernel."""

        status = self.ghost_rpc.status()
        status.update(
            {
                "mode": self._mode,
                "running": self._running,
                "proxy_mode": self.proxy_manager.mode,
                "proxies": self.proxy_manager.proxies,
            }
        )
        return status

    def mesh_snapshot(self) -> MutableMapping[str, object]:
        """Return the last computed mesh snapshot."""

        if not self._mesh_cache:
            self._mesh_cache = self._build_mesh_snapshot()
        return dict(self._mesh_cache)

    def _build_mesh_snapshot(self) -> MutableMapping[str, object]:
        nodes = self.ghost_rpc.iter_nodes()
        if not nodes:
            return {"timestamp": time.time(), "nodes": [], "edges": []}

        labels = self.cluster_engine.cluster_seeds([node.geometry for node in nodes])
        self.ghost_rpc.assign_clusters(labels)

        cluster_map: Dict[int, List[PhantomNode]] = {}
        payload_nodes: List[MutableMapping[str, object]] = []
        for node, label in zip(nodes, labels):
            node.cluster = int(label)
            cluster_map.setdefault(node.cluster, []).append(node)
            payload_nodes.append(
                {
                    "id": node.identifier,
                    "position": node.position3d(),
                    "cluster": node.cluster,
                    "weight": round(float(node.weight), 4),
                    "active": node.active,
                }
            )

        edges: List[MutableMapping[str, object]] = []
        max_edges = max(1, self._max_edges_per_cluster)
        for cluster_nodes in cluster_map.values():
            cluster_nodes.sort(key=lambda n: n.identifier)
            for idx in range(min(len(cluster_nodes) - 1, max_edges)):
                src = cluster_nodes[idx]
                dst = cluster_nodes[(idx + 1) % len(cluster_nodes)]
                edges.append(
                    {
                        "source": src.identifier,
                        "target": dst.identifier,
                        "weight": round((src.weight + dst.weight) / 2, 4),
                    }
                )

        return {
            "timestamp": time.time(),
            "nodes": payload_nodes,
            "edges": edges,
        }

    def export_mesh(self, *, format: str = "json", filename: str | None = None) -> Path:
        """Persist the current mesh snapshot in the requested format."""

        snapshot = self.mesh_snapshot()
        if filename is None:
            filename = f"mesh_phantom.{format}"
        if format == "json":
            return self.export.export_as_json(snapshot, filename=filename)
        if format == "csv":
            rows: Iterable[Sequence[object]] = [
                (n["id"], *(n["position"]), n["cluster"], n["weight"])
                for n in snapshot.get("nodes", [])
            ]
            return self.export.export_as_csv(rows, filename=filename)
        if format == "obj":
            path = Path(self.export.export_dir) / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as handle:
                for node in snapshot.get("nodes", []):
                    x, y, z = node["position"]
                    handle.write(f"v {x} {y} {z}\n")
                for edge in snapshot.get("edges", []):
                    src_idx = self._index_of_node(snapshot["nodes"], edge["source"]) + 1
                    dst_idx = self._index_of_node(snapshot["nodes"], edge["target"]) + 1
                    if src_idx and dst_idx:
                        handle.write(f"l {src_idx} {dst_idx}\n")
            return path
        raise ValueError(f"Unsupported mesh export format: {format}")

    @staticmethod
    def _index_of_node(nodes: Sequence[MutableMapping[str, object]], identifier: str) -> int:
        for index, node in enumerate(nodes):
            if node.get("id") == identifier:
                return index
        return 0

    def supervisor_params(self) -> MutableMapping[str, float]:
        """Expose the current supervisor snapshot."""

        return self.supervisor.snapshot()

    def apply_supervisor_update(self, params: MutableMapping[str, float]) -> None:
        """Update supervisor state with custom parameters."""

        self.supervisor.update(params)


__all__ = [
    "PhantomNode",
    "ProxyManager",
    "OuroborosQuadrupole",
    "GhostRPCEngine",
    "PhantomloadKernel",
]
