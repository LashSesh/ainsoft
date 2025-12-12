"""Core orchestrator for the Phantomload expansion."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import threading
import time
from typing import Deque, Dict, List, Optional

from ainsoft.pipeline.web3suite import MetaMemoryCore, ScorpioBridge

from .cell_manager import PhantomCellManager
from .ghost_rpc import GhostRPCManager, GhostRPCNode
from .heatmap import HeatmapExporter
from .ouroboros import OuroborosQuadrupole
from .proxy_manager import ProxyManager
from .supervisor import PhantomloadSupervisor


@dataclass
class PhantomloadEvent:
    """Represents a telemetry event emitted by the kernel."""

    event_id: int
    timestamp: float
    payload: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        """Return a serialisable representation."""

        data = dict(self.payload)
        data["event_id"] = self.event_id
        data["timestamp"] = self.timestamp
        return data


class PhantomloadKernel:
    """Coordinates phantomload simulations, telemetry, and exports."""

    def __init__(self, config: Optional[Dict[str, object]] = None) -> None:
        self.config = config or {}
        self.supervisor = PhantomloadSupervisor()
        self.supervisor.configure(
            {
                "default_mode": self.config.get("default_mode", "sybil"),
                "default_nodes": self.config.get("default_nodes", 32),
                "heartbeat": self.config.get("heartbeat", 0.017),
                "quadrupole_mode": self.config.get("quadrupole_mode", True),
                "mesh_export_format": self.config.get("mesh_export_format", "json"),
                "mesh_view": self.config.get("mesh_view", "traffic"),
            }
        )
        self.proxy_manager = ProxyManager()
        if proxy_cfg := self.config.get("proxy"):
            self.proxy_manager.configure(proxy_cfg)

        self.cell_manager = PhantomCellManager()
        self.heatmap_exporter = HeatmapExporter()
        self.meta_memory = MetaMemoryCore()
        self.quadrupole = OuroborosQuadrupole()
        self.rpc_manager = GhostRPCManager(self.proxy_manager)

        self._event_lock = threading.Lock()
        self._events: Deque[PhantomloadEvent] = deque(maxlen=512)
        self._event_counter = 0

        self._bridge = ScorpioBridge(tick_interval=self.supervisor.get_param("heartbeat"))
        self._bridge.register_callback(self._on_tick)
        self._bridge_started = False

    def _ensure_bridge(self) -> None:
        if not self._bridge_started:
            self._bridge.start()
            self._bridge_started = True

    def configure(self, payload: Dict[str, object]) -> None:
        """Merge runtime configuration updates."""

        heartbeat = payload.get("heartbeat")
        if heartbeat and heartbeat != self.supervisor.get_param("heartbeat"):
            self._bridge.stop()
            self._bridge_started = False
            self._bridge = ScorpioBridge(tick_interval=float(heartbeat))
            self._bridge.register_callback(self._on_tick)
        self.supervisor.configure(payload)

    def trigger(
        self,
        *,
        mode: Optional[str] = None,
        nodes: Optional[int] = None,
        pattern: str = "quadrupole",
        endpoint: str = "http://localhost:8545",
        base_phrase: Optional[str] = None,
    ) -> Dict[str, object]:
        """Start a phantomload wave and return its snapshot."""

        mode = mode or str(self.supervisor.get_param("default_mode"))
        nodes = int(nodes or self.supervisor.get_param("default_nodes"))
        base_phrase = base_phrase or f"phantom-seed-{int(time.time())}"
        cells = self.cell_manager.spawn_cells(nodes, base_phrase)
        rpc_nodes: List[GhostRPCNode] = []
        for cell in cells:
            rpc_nodes.append(
                GhostRPCNode(
                    node_id=cell.cell_id,
                    endpoint=endpoint,
                    seed=cell.seed_phrase,
                    metadata={"cluster": cell.cluster, "score": cell.score()},
                )
            )
        wave = self.rpc_manager.start_wave(mode=mode, pattern=pattern, nodes=rpc_nodes, endpoint=endpoint)
        self._ensure_bridge()
        self._record_event({"type": "wave_started", "wave": wave.snapshot()})
        return wave.snapshot()

    def stop(self) -> None:
        """Stop the active phantomload wave."""

        self.rpc_manager.stop_wave()
        self._record_event({"type": "wave_stopped"})
        if self._bridge_started:
            self._bridge.stop()
            self._bridge_started = False

    def status(self) -> Dict[str, object]:
        """Return the current kernel status."""

        status = self.rpc_manager.status()
        status["quadrupole"] = self.quadrupole.summary()
        status["cells"] = self.cell_manager.cell_count()
        status["supervisor"] = self.supervisor.get_params()
        status["proxy"] = self.proxy_manager.snapshot()
        return status

    def export_mesh(self, *, fmt: Optional[str] = None) -> Dict[str, object] | str:
        """Export the mesh state as JSON or OBJ string."""

        fmt = fmt or str(self.supervisor.get_param("mesh_export_format"))
        mesh = self.cell_manager.to_mesh(view=self.supervisor.get_param("mesh_view"))
        if fmt == "obj":
            return self._mesh_to_obj(mesh)
        return mesh

    def mesh_view(self, view: Optional[str] = None) -> Dict[str, object]:
        """Return a mesh snapshot for Unity visualisation."""

        view = view or str(self.supervisor.get_param("mesh_view"))
        return self.cell_manager.to_mesh(view=view)

    def heatmap(self) -> List[Dict[str, object]]:
        """Return heatmap data for the current cells."""

        return self.heatmap_exporter.build(self.cell_manager.iter_cells())

    def supervisor_params(self) -> Dict[str, object]:
        """Return supervisor parameters."""

        return self.supervisor.get_params()

    def set_supervisor_param(self, name: str, value: object) -> Dict[str, object]:
        """Update a supervisor parameter."""

        updated = self.supervisor.set_param(name, value)
        self._record_event({"type": "param_update", "name": name, "value": value})
        return updated

    def configure_proxy(self, payload: Dict[str, object]) -> Dict[str, object]:
        """Update proxy configuration."""

        snapshot = self.proxy_manager.configure(payload)
        self._record_event({"type": "proxy_update", "config": snapshot})
        return snapshot

    def stream_events(self, last_event_id: Optional[int] = None) -> List[Dict[str, object]]:
        """Return events newer than ``last_event_id``."""

        with self._event_lock:
            events = [event.to_dict() for event in self._events if last_event_id is None or event.event_id > last_event_id]
        return events

    def _mesh_to_obj(self, mesh: Dict[str, object]) -> str:
        """Convert the mesh snapshot into an OBJ-like string."""

        lines: List[str] = []
        nodes = mesh.get("nodes", [])
        for node in nodes:
            x, y, z = node["position"]
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")
        index_map = {node["id"]: idx + 1 for idx, node in enumerate(nodes)}
        for edge in mesh.get("edges", []):
            src = index_map.get(edge["source"])
            dst = index_map.get(edge["target"])
            if src is None or dst is None:
                continue
            lines.append(f"l {src} {dst}")
        return "\n".join(lines)

    def _on_tick(self) -> None:
        """Heartbeat callback linking wave, quadrupole, and telemetry."""

        self.quadrupole.advance()
        self._record_event({"type": "quadrupole", "state": self.quadrupole.summary()})
        activity = self.rpc_manager.tick()
        if activity:
            self._record_event({"type": "wave_tick", "activity": activity})
            self.meta_memory.store({
                "timestamp": activity["timestamp"],
                "requests": activity["wave"]["metrics"]["requests"],
            })

    def _record_event(self, payload: Dict[str, object]) -> None:
        with self._event_lock:
            event = PhantomloadEvent(event_id=self._event_counter, timestamp=time.time(), payload=payload)
            self._events.append(event)
            self._event_counter += 1

    def shutdown(self) -> None:
        """Stop all background activity and reset state."""

        self.stop()
        self.cell_manager.reset()
        with self._event_lock:
            self._events.clear()
            self._event_counter = 0
