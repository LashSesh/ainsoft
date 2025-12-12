"""AinSOFT Graphical Control Center (PyQt6 GUI).

This module provides a production-ready PyQt6 user interface that exposes the
major AinSOFT subsystems described in the project README.  It combines a modern
multi-pane layout, asynchronous task execution and visual telemetry to offer a
comprehensive operator cockpit for mesh, traffic and diagnostic tooling.  The
Web3 expansion pack is treated as an optional module that operators can enable
explicitly, ensuring the default experience focuses on the core traffic
resonance laboratory workflows.
"""

from __future__ import annotations

import copy
import json
import logging
import random
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import yaml

from PyQt6.QtCore import (
    QLocale,
    QObject,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QTranslator,
    QRunnable,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPalette, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QDoubleSpinBox,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:  # pragma: no cover - optional matplotlib integration
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure

    MPL_AVAILABLE = True
except Exception:  # pragma: no cover - fallback if matplotlib missing
    FigureCanvasQTAgg = object  # type: ignore
    Figure = object  # type: ignore
    MPL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Local package import guard
# ---------------------------------------------------------------------------


if __package__ in {None, ""}:  # pragma: no cover - runtime convenience guard
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


from ainsoft.config import (  # noqa: E402  - import after PyQt to avoid qtpy detection
    DEFAULT_PIPELINE_CONFIG,
    DEFAULT_PROXY_CONFIG,
    load_phosphoros_web3_config,
    load_phantomload_config,
)
from ainsoft.orchestrator.lifecycle import run_lifecycle_cycle  # noqa: E402
from ainsoft.pipeline import (  # noqa: E402
    MeshLayer,
    PointCloud,
    ReverbRing,
    SeedClusterEngine,
    SeedDNAEngine,
    SupervisorInterface,
    MetaMemoryCore,
    ExportModule,
    PhosphorosKernel,
    ScorpioBridge,
    PhantomloadKernel,
    example_grad_func,
    example_score_func,
    example_targeting_func,
)
from ainsoft.pipeline.aion_pipeline import (  # noqa: E402
    PipelineOrchestrator,
    build_fixpunkt_engine_from_config,
    build_orchestrator_from_config,
)


# ---------------------------------------------------------------------------
# Logging infrastructure
# ---------------------------------------------------------------------------


class LogSignalEmitter(QObject):
    """Qt signal bridge forwarding Python log records to the UI."""

    log_record = pyqtSignal(str, str)


class QtLogHandler(logging.Handler):
    """Custom logging handler that forwards messages to the GUI console."""

    def __init__(self, emitter: LogSignalEmitter) -> None:
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin wrapper
        message = self.format(record)
        self.emitter.log_record.emit(record.levelname, message)


class LogConsole(QTextEdit):
    """Colour-coded log console for module panels."""

    COLORS = {
        "DEBUG": QColor("#6c757d"),
        "INFO": QColor("#00a896"),
        "WARNING": QColor("#f77f00"),
        "ERROR": QColor("#d62828"),
        "CRITICAL": QColor("#9d0208"),
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("LogConsole")
        self.setMinimumHeight(160)

    def append_message(self, level: str, message: str) -> None:
        """Append a message using the configured colour palette."""

        color = self.COLORS.get(level.upper(), QColor("#ffffff"))
        self.setTextColor(color)
        self.append(f"[{level.upper()}] {message}")
        self.moveCursor(QTextCursor.MoveOperation.End)


# ---------------------------------------------------------------------------
# Worker infrastructure
# ---------------------------------------------------------------------------


class WorkerSignals(QObject):
    """Signals produced by :class:`Worker` tasks."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    started = pyqtSignal()


class Worker(QRunnable):
    """Generic worker executing a callable on the thread pool."""

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:  # pragma: no cover - background thread
        try:
            self.signals.started.emit()
            result = self.func(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - user facing message
            logging.exception("Worker execution failed: %s", exc)
            self.signals.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------


class StatusIndicator(QLabel):
    """Pill-shaped status label used in module headers."""

    def __init__(self, text: str = "Idle", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._status = "idle"
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(24)
        self.update_status("idle")

    def update_status(self, status: str) -> None:
        """Update the textual and visual state."""

        self._status = status
        palette = {
            "idle": "#6c757d",
            "running": "#1b998b",
            "warning": "#f77f00",
            "error": "#d62828",
            "success": "#118ab2",
        }
        colour = palette.get(status, "#6c757d")
        self.setStyleSheet(
            """
            QLabel {
                border-radius: 12px;
                padding: 2px 12px;
                color: white;
                background-color: %s;
                font-weight: 600;
            }
            """
            % colour
        )


class PreviewCanvas(QWidget):
    """Wrapper that renders matplotlib previews or graceful fallbacks.

    TODO: Replace this placeholder with a Unity/Unreal powered viewport once
    the Seraphic Swarm visualiser is integrated into the desktop client.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        if MPL_AVAILABLE:
            self.figure = Figure(figsize=(5, 3))
            self.canvas = FigureCanvasQTAgg(self.figure)
            layout.addWidget(self.canvas)
        else:  # pragma: no cover - fallback mode
            self.figure = None
            self.canvas = QLabel("Matplotlib not available. Install matplotlib for previews.")
            self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.canvas.setWordWrap(True)
            layout.addWidget(self.canvas)

    def plot_heatmap(self, data: List[MutableMapping[str, float]]) -> None:
        """Render a heatmap-style preview from ReverbRing logs."""

        if not MPL_AVAILABLE:
            return
        ax = self.figure.subplots()  # type: ignore[assignment]
        ax.clear()
        if not data:
            ax.text(0.5, 0.5, "No activity", ha="center", va="center")
        else:
            timestamps = [entry.get("timestamp", idx) for idx, entry in enumerate(data)]
            metrics = [entry.get("seed") or entry.get("mutant") or entry.get("n_seeds", 0.0) for entry in data]
            ax.plot(timestamps, metrics, marker="o", linestyle="-", color="#118ab2")
            ax.set_xlabel("Timestamp")
            ax.set_ylabel("Resonance")
            ax.set_title("ReverbRing Activity")
        self.canvas.draw()

    def plot_pointcloud(self, pointcloud: PointCloud) -> None:
        """Render the first three dimensions of a point cloud."""

        if not MPL_AVAILABLE:
            return
        points = pointcloud.as_array()
        ax = self.figure.subplots()  # type: ignore[assignment]
        ax.clear()
        if hasattr(points, "shape") and points.shape[0] and points.shape[1] >= 3:
            xs = [float(row[0]) for row in points]
            ys = [float(row[1]) for row in points]
            zs = [float(row[2]) for row in points]
            ax.scatter(xs, ys, c=zs, cmap="viridis")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_title("PointCloud Preview (3D projected)")
        elif len(points):
            xs = [float(row[0]) for row in points]
            ys = [float(row[1]) for row in points]
            ax.scatter(xs, ys, color="#06d6a0")
            ax.set_title("PointCloud Preview (2D)")
        else:
            ax.text(0.5, 0.5, "PointCloud empty", ha="center", va="center")
        self.canvas.draw()

    def plot_mesh_edges(self, meshlayer: MeshLayer) -> None:
        """Visualise mesh edge weights."""

        if not MPL_AVAILABLE:
            return
        ax = self.figure.subplots()  # type: ignore[assignment]
        ax.clear()
        edges = meshlayer.meshbuilder.edge_scores
        if not edges:
            ax.text(0.5, 0.5, "Mesh not weighted", ha="center", va="center")
        else:
            scores = list(edges.values())
            ax.hist(scores, bins=min(len(scores), 10), color="#073b4c", alpha=0.8)
            ax.set_title("Mesh Edge Score Distribution")
        self.canvas.draw()

    def plot_series(self, values: Sequence[float], *, title: str, ylabel: str) -> None:
        """Plot a simple time-series style chart from numeric values."""

        if not MPL_AVAILABLE:
            return
        ax = self.figure.subplots()  # type: ignore[assignment]
        ax.clear()
        if not values:
            ax.text(0.5, 0.5, "No datapoints", ha="center", va="center")
        else:
            ax.plot(range(len(values)), values, marker="o", color="#00FFF7")
            ax.set_xlabel("Execution")
            ax.set_ylabel(ylabel)
            ax.set_title(title)
        self.canvas.draw()

    def plot_network_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        """Visualise phantomload mesh snapshots."""

        if not MPL_AVAILABLE:
            return
        ax = self.figure.subplots()  # type: ignore[assignment]
        ax.clear()
        nodes = snapshot.get("nodes", []) if isinstance(snapshot, Mapping) else []
        if not nodes:
            ax.text(0.5, 0.5, "Traffic mesh idle", ha="center", va="center")
            self.canvas.draw()
            return
        xs = [float(node.get("position", [0])[0]) for node in nodes]
        ys = [float(node.get("position", [0, 0])[1]) for node in nodes]
        colours = [float(node.get("cluster", 0)) for node in nodes]
        scatter = ax.scatter(xs, ys, c=colours, cmap="plasma", alpha=0.85)
        ax.set_title("Traffic Resonance Nodes")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        if nodes and hasattr(ax.figure, "colorbar"):
            ax.figure.colorbar(scatter, ax=ax, label="Cluster")
        self.canvas.draw()


# ---------------------------------------------------------------------------
# Controller layer
# ---------------------------------------------------------------------------


class AppController(QObject):
    """Central controller exposing backend operations to the UI layer."""

    log_event = pyqtSignal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.thread_pool = QThreadPool()
        self.pointcloud = PointCloud()
        self.meshlayer: Optional[MeshLayer] = None
        self.reverb_ring = ReverbRing()
        self.supervisor = SupervisorInterface()
        self.meta_memory = MetaMemoryCore(max_history=64)
        self.bridge = ScorpioBridge()
        self.traffic_bridge = ScorpioBridge(tick_interval=0.05)
        self.kernel: Optional[PhosphorosKernel] = None
        self.web3_enabled = False
        self.quantum_enabled = False
        self.phantom_enabled = True
        self.lifecycle_proxy: MutableMapping[str, Any] = copy.deepcopy(DEFAULT_PROXY_CONFIG)
        self.lifecycle_history: List[MutableMapping[str, Any]] = []
        phantom_cfg = load_phantomload_config()
        self.phantom_kernel = PhantomloadKernel.from_config(
            phantom_cfg,
            export_dir=Path.cwd() / "exports" / "phantom",
        )
        self.phantom_kernel.bridge = self.traffic_bridge
        self.phantom_kernel.supervisor = self.supervisor
        self.phantom_kernel.meta_memory = self.meta_memory
        self.phantom_kernel.reverb = self.reverb_ring
        self.phantom_config: MutableMapping[str, Any] = phantom_cfg
        self.pipeline_config: MutableMapping[str, Any] = copy.deepcopy(DEFAULT_PIPELINE_CONFIG)
        self.proxy_config: MutableMapping[str, Any] = copy.deepcopy(DEFAULT_PROXY_CONFIG)
        self.orchestrator: PipelineOrchestrator = build_orchestrator_from_config(
            self.pipeline_config.get("pipeline", {})
        )
        self.pipeline_history: List[Mapping[str, Any]] = []
        self.fixpunkt_last_result: Optional[MutableMapping[str, Any]] = None
        self._bridge_lock = threading.Lock()
        self._bridge_running = False
        self._last_config: MutableMapping[str, Any] = {}
        self.log_event.connect(self._log)

    # ------------------------------------------------------------------
    # Web3 kernel lifecycle
    # ------------------------------------------------------------------

    def set_web3_enabled(self, enabled: bool) -> None:
        """Enable or disable the optional Web3 expansion pack."""

        if enabled == self.web3_enabled:
            return
        self.web3_enabled = enabled
        if enabled:
            self.kernel = self._create_web3_kernel()
            self.log_event.emit("INFO", "Web3 expansion activated")
        else:
            tick_interval = self.bridge.tick_interval
            if self._bridge_running:
                self.bridge_stop()
            self.bridge = ScorpioBridge(tick_interval=tick_interval)
            self.kernel = None
            self.log_event.emit("INFO", "Web3 expansion deactivated")

    def set_quantum_enabled(self, enabled: bool) -> None:
        """Toggle availability of the Quantum Finance expansion."""

        if enabled == self.quantum_enabled:
            return
        self.quantum_enabled = enabled
        message = "Quantum Finance expansion activated" if enabled else "Quantum Finance expansion deactivated"
        self.log_event.emit("INFO", message)

    def set_phantom_enabled(self, enabled: bool) -> None:
        """Toggle Phantomload expansion tooling."""

        if enabled == self.phantom_enabled:
            return
        self.phantom_enabled = enabled
        if not enabled:
            self.phantom_kernel.stop()
        message = "Phantomload expansion activated" if enabled else "Phantomload expansion deactivated"
        self.log_event.emit("INFO", message)

    def _create_web3_kernel(self) -> PhosphorosKernel:
        kernel = PhosphorosKernel(
            bridge=self.bridge,
            dna_engine=SeedDNAEngine(),
            cluster_engine=SeedClusterEngine(n_clusters=3),
            meta_memory=self.meta_memory,
            export=ExportModule(export_dir=Path.cwd() / "exports"),
        )
        kernel.reverb = self.reverb_ring
        kernel.supervisor = self.supervisor
        kernel.meta_memory = self.meta_memory
        kernel.attach_default_tick()
        return kernel

    def ensure_web3_kernel(self) -> PhosphorosKernel:
        if not self.web3_enabled or self.kernel is None:
            raise RuntimeError(
                "Web3 expansion is disabled. Enable it from Settings to access these controls."
            )
        return self.kernel

    def seed_counts(self) -> Tuple[int, int]:
        kernel = self.kernel if self.web3_enabled and self.kernel is not None else None
        if kernel is None:
            return (0, 0)
        clusters = getattr(kernel, "clusters", [])
        return len(kernel.seeds), len(clusters)

    def seed_vectors(self) -> List[List[float]]:
        kernel = self.ensure_web3_kernel()
        vectors: List[List[float]] = []
        for seed in kernel.seeds:
            if hasattr(seed, "tolist"):
                raw = seed.tolist()
            else:
                raw = list(seed)
            vectors.append([float(value) for value in raw])
        return vectors

    def kernel_snapshot(self) -> MutableMapping[str, Any]:
        kernel = self.ensure_web3_kernel()
        seeds = self.seed_vectors()
        return {
            "seeds": seeds,
            "clusters": list(getattr(kernel, "clusters", [])),
            "history": self.meta_history(),
            "supervisor": self.supervisor_snapshot(),
        }

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, level: str, message: str) -> None:
        logging.getLogger(__name__).log(getattr(logging, level.upper(), logging.INFO), message)

    # ------------------------------------------------------------------
    # PointCloud / Mesh operations
    # ------------------------------------------------------------------

    def generate_pointcloud(self, count: int, dimensions: int) -> PointCloud:
        """Generate a random point cloud used throughout the GUI."""

        if count <= 0 or dimensions <= 0:
            raise ValueError("Point count and dimensions must be positive")
        points = []
        for _ in range(count):
            points.append([random.random() for _ in range(dimensions)])
        self.pointcloud = PointCloud(points, dimensions=dimensions)
        self.log_event.emit("INFO", f"Generated pointcloud with {count} points in {dimensions}D")
        return self.pointcloud

    def load_pointcloud_from_file(self, path: Path) -> PointCloud:
        """Load a point cloud from a JSON or CSV file."""

        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            points = data.get("points") if isinstance(data, dict) else data
        else:
            rows: List[List[float]] = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        rows.append([float(value) for value in line.strip().split(",") if value])
                    except ValueError as exc:  # noqa: BLE001 - input validation
                        raise ValueError(f"Invalid numeric value in {path}") from exc
            points = rows
        self.pointcloud = PointCloud(points)
        self.log_event.emit("INFO", f"Loaded pointcloud from {path.name}")
        return self.pointcloud

    def build_meshlayer(self, mode: str = "knn", k: int = 5) -> MeshLayer:
        """Create a MeshLayer from the current point cloud."""

        if not self.pointcloud.as_array():
            raise RuntimeError("PointCloud is empty. Generate or load data first.")
        self.meshlayer = MeshLayer(self.pointcloud.as_array(), mode=mode, k=k)
        self.meshlayer.build_mesh()
        self.log_event.emit("INFO", f"Mesh built using mode={mode} and k={k}")
        return self.meshlayer

    def weight_mesh_edges(self) -> None:
        """Apply the default scoring function to mesh edges."""

        if not self.meshlayer:
            raise RuntimeError("No mesh available. Build mesh first.")
        self.meshlayer.weight_edges(example_score_func)
        self.log_event.emit("INFO", "Weighted mesh edges via example_score_func")

    def solve_mesh(self) -> None:
        if not self.meshlayer:
            raise RuntimeError("No mesh available. Build mesh first.")
        self.meshlayer.solve()
        self.log_event.emit("INFO", "Executed solve operator")

    def gate_mesh(self, threshold: float) -> None:
        if not self.meshlayer:
            raise RuntimeError("No mesh available. Build mesh first.")
        self.meshlayer.gate(threshold)
        self.log_event.emit("INFO", f"Applied gate threshold={threshold:.2f}")

    def coagula_mesh(self) -> Dict[int, int]:
        if not self.meshlayer:
            raise RuntimeError("No mesh available. Build mesh first.")
        clusters = self.meshlayer.coagula()
        self.log_event.emit("INFO", f"Coagula produced {len(clusters)} assignments")
        return clusters

    def expand_mesh(self, step: float = 0.05) -> None:
        if not self.meshlayer:
            raise RuntimeError("No mesh available. Build mesh first.")
        self.meshlayer.expand(example_grad_func, step=step)
        self.log_event.emit("INFO", f"Expanded mesh using gradient step={step}")

    def audit_mesh(self) -> List[str]:
        if not self.meshlayer:
            raise RuntimeError("No mesh available. Build mesh first.")
        events = [f"{event.event}: {event.info}" for event in self.meshlayer.audit()]
        self.log_event.emit("INFO", f"Mesh audit contains {len(events)} events")
        return events

    def export_mesh(self, path: Path) -> Path:
        if not self.meshlayer:
            raise RuntimeError("No mesh available. Build mesh first.")
        self.meshlayer.export_json(str(path))
        self.log_event.emit("INFO", f"Mesh exported to {path}")
        return path

    def import_mesh(self, path: Path) -> MeshLayer:
        layer = MeshLayer.import_state(str(path))
        self.meshlayer = layer
        self.log_event.emit("INFO", f"MeshLayer imported from {path.name}")
        return layer

    def refresh_pointcloud(self, count: int = 256) -> PointCloud:
        """Generate a refreshed pointcloud using the current dimensionality."""

        dimensions = getattr(self.pointcloud, "dimensions", None) or 5
        self.log_event.emit("INFO", "Triggering sensor sweep for pointcloud refresh")
        return self.generate_pointcloud(count, int(dimensions))

    # ------------------------------------------------------------------
    # Web3 kernel operations
    # ------------------------------------------------------------------

    def add_seed_phrase(self, phrase: str, mutate: bool = False) -> List[float]:
        if not phrase.strip():
            raise ValueError("Seed phrase cannot be empty")
        kernel = self.ensure_web3_kernel()
        geometry = kernel.add_seed_phrase(phrase, mutate=mutate)
        self.log_event.emit("INFO", f"Added seed phrase '{phrase[:8]}…'")
        return geometry.tolist()

    def cluster_seeds(self) -> List[int]:
        kernel = self.ensure_web3_kernel()
        labels = kernel.cluster()
        self.log_event.emit("INFO", f"Clustered {len(kernel.seeds)} seeds")
        return labels

    def export_kernel_state(self, filename: str) -> Path:
        kernel = self.ensure_web3_kernel()
        path = kernel.export_state(filename=filename)
        self.log_event.emit("INFO", f"Kernel state exported to {path}")
        return path

    def bridge_start(self) -> None:
        with self._bridge_lock:
            if self._bridge_running:
                return
            self.bridge.start()
            self._bridge_running = True
        self.log_event.emit("INFO", "ScorpioBridge heartbeat started")

    def bridge_stop(self) -> None:
        with self._bridge_lock:
            if not self._bridge_running:
                return
            self.bridge.stop()
            self._bridge_running = False
        self.log_event.emit("INFO", "ScorpioBridge heartbeat stopped")

    def supervisor_snapshot(self) -> MutableMapping[str, float]:
        snapshot = self.supervisor.snapshot()
        self.log_event.emit("DEBUG", f"Supervisor snapshot: {snapshot}")
        return snapshot

    def meta_history(self) -> List[MutableMapping[str, float]]:
        return self.meta_memory.get_history()

    def reverb_activity(self) -> List[MutableMapping[str, float]]:
        return self.reverb_ring.get_heatmap()

    # ------------------------------------------------------------------
    # Resonance lifecycle / targeting operations
    # ------------------------------------------------------------------

    def set_lifecycle_proxy(self, config: Mapping[str, Any]) -> None:
        self.lifecycle_proxy.update(
            {
                "enabled": config.get("enabled", self.lifecycle_proxy.get("enabled", False)),
                "host": config.get("host", self.lifecycle_proxy.get("host")),
                "port": config.get("port", self.lifecycle_proxy.get("port")),
                "username": config.get("username", self.lifecycle_proxy.get("username")),
                "password": config.get("password", self.lifecycle_proxy.get("password")),
            }
        )
        state = "enabled" if self.lifecycle_proxy.get("enabled") else "disabled"
        self.log_event.emit("INFO", f"Lifecycle proxy routing {state}")

    def run_resonance_cycles(
        self,
        target: str,
        port: int,
        cycles: int,
        proxy_overrides: Optional[Mapping[str, Any]] = None,
    ) -> MutableMapping[str, Any]:
        if not target.strip():
            raise ValueError("Target host or IP must be provided")
        if port <= 0 or port > 65535:
            raise ValueError("Target port must be between 1 and 65535")
        if cycles <= 0:
            raise ValueError("Number of cycles must be positive")

        proxy_config = copy.deepcopy(self.lifecycle_proxy)
        if proxy_overrides:
            proxy_config.update({k: v for k, v in proxy_overrides.items() if v is not None})

        if proxy_config.get("enabled") and (not proxy_config.get("host") or not proxy_config.get("port")):
            raise ValueError("Proxy enabled but host/port missing")

        cycle_data: List[MutableMapping[str, Any]] = []
        start = time.perf_counter()
        for index in range(cycles):
            cycle_start = time.perf_counter()
            run_lifecycle_cycle(target, port, proxy_config=proxy_config)
            duration = time.perf_counter() - cycle_start
            cycle_data.append({"cycle": index + 1, "duration": duration})
        total_duration = time.perf_counter() - start
        record: MutableMapping[str, Any] = {
            "target": target,
            "port": port,
            "cycles": cycles,
            "timeline": cycle_data,
            "total_duration": total_duration,
            "timestamp": time.time(),
            "proxy": proxy_config,
        }
        self.lifecycle_history.append(record)
        self.log_event.emit(
            "INFO",
            f"Executed {cycles} resonance cycle(s) targeting {target}:{port}",
        )
        return record

    def resonance_history(self) -> List[MutableMapping[str, Any]]:
        return list(self.lifecycle_history)

    def resonance_metrics(self) -> List[float]:
        if not self.lifecycle_history:
            return []
        timeline = self.lifecycle_history[-1].get("timeline", [])
        return [float(entry.get("duration", 0.0)) for entry in timeline]

    # ------------------------------------------------------------------
    # Pipeline orchestration & Fixpunkt engine
    # ------------------------------------------------------------------

    def refresh_orchestrator(self, pipeline_config: Optional[Mapping[str, Any]] = None) -> None:
        config = pipeline_config or self.pipeline_config.get("pipeline", {})
        self.orchestrator = build_orchestrator_from_config(config)

    def apply_pipeline_blueprint(self, config: Mapping[str, Any]) -> None:
        self.pipeline_config["pipeline"] = copy.deepcopy(config.get("pipeline", {}))
        if "fixpunkt" in config:
            self.pipeline_config["fixpunkt"] = copy.deepcopy(config.get("fixpunkt", {}))
        self.refresh_orchestrator()
        self.log_event.emit("INFO", "Pipeline blueprint applied to orchestrator")

    def update_proxy_settings(
        self,
        *,
        enabled: bool,
        host: Optional[str],
        port: Optional[int],
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.proxy_config.update(
            {
                "enabled": enabled,
                "host": host,
                "port": port,
                "username": username,
                "password": password,
            }
        )
        state = "enabled" if enabled else "disabled"
        self.log_event.emit("INFO", f"Proxy routing {state} for orchestrator")

    def run_pipeline_cycle(self) -> List[Mapping[str, Any]]:
        if not self.orchestrator.generators:
            raise RuntimeError("No generators configured for the orchestrator")
        results = self.orchestrator.run(proxy_cfg=self.proxy_config)
        self.pipeline_history = results
        self.log_event.emit("INFO", f"Pipeline executed with {len(results)} generator passes")
        return results

    def pipeline_stage_lengths(self) -> List[int]:
        return [len(item.get("stages", [])) for item in self.pipeline_history]

    def run_fixpunkt_cycle(self) -> Optional[MutableMapping[str, Any]]:
        engine = build_fixpunkt_engine_from_config(self.pipeline_config, proxy_cfg=self.proxy_config)
        candidate = engine.run()
        if candidate is None:
            self.fixpunkt_last_result = None
            self.log_event.emit("WARNING", "Fixpunkt attractor returned no consensus candidate")
            return None
        result = {"value": candidate.value, "metadata": dict(candidate.metadata)}
        self.fixpunkt_last_result = result
        self.log_event.emit("INFO", "Fixpunkt consensus candidate resolved")
        return result

    # ------------------------------------------------------------------
    # Phantomload / traffic resonance operations
    # ------------------------------------------------------------------

    def apply_phantom_config(self, config: Mapping[str, Any]) -> None:
        self.phantom_kernel.stop()
        self.phantom_config = copy.deepcopy(config)
        kernel = PhantomloadKernel.from_config(
            self.phantom_config,
            export_dir=Path.cwd() / "exports" / "phantom",
        )
        kernel.supervisor = self.supervisor
        kernel.meta_memory = self.meta_memory
        kernel.reverb = self.reverb_ring
        kernel.bridge = self.traffic_bridge
        self.phantom_kernel = kernel
        self.log_event.emit("INFO", "Traffic resonance kernel reconfigured")

    def launch_resonance_pulse(
        self,
        *,
        mode: str,
        nodes: int,
        mutate: bool = True,
        autostart: bool = True,
    ) -> MutableMapping[str, Any]:
        if not self.phantom_enabled:
            raise RuntimeError("Phantomload expansion disabled. Enable it from Settings to launch pulses.")
        status = self.phantom_kernel.trigger(mode=mode, nodes=nodes, mutate=mutate, autostart=autostart)
        self.log_event.emit("INFO", f"Resonance pulse '{mode}' launched with {nodes} nodes")
        return status

    def halt_resonance_pulse(self) -> None:
        self.phantom_kernel.stop()
        self.log_event.emit("INFO", "Resonance pulse halted")

    def phantom_status(self) -> MutableMapping[str, Any]:
        if not self.phantom_enabled:
            return {"status": "disabled", "nodes": 0, "events": 0}
        return self.phantom_kernel.status()

    def phantom_mesh_snapshot(self) -> MutableMapping[str, Any]:
        if not self.phantom_enabled:
            return {"nodes": [], "edges": []}
        return self.phantom_kernel.mesh_snapshot()

    def phantom_update_proxies(self, proxies: Sequence[str], mode: str = "round_robin") -> None:
        if not self.phantom_enabled:
            raise RuntimeError("Phantomload expansion disabled. Enable it from Settings to manage proxies.")
        clean = [proxy.strip() for proxy in proxies if proxy.strip()]
        self.phantom_kernel.configure_proxy(clean, mode=mode)
        self.log_event.emit("INFO", f"Phantom proxy rotation set to {mode} with {len(clean)} entries")

    def export_phantom_mesh(self, path: Path) -> Path:
        if not self.phantom_enabled:
            raise RuntimeError("Phantomload expansion disabled. Enable it from Settings to export meshes.")
        snapshot = self.phantom_kernel.mesh_snapshot()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        self.log_event.emit("INFO", f"Traffic resonance mesh exported to {path}")
        return path

    # ------------------------------------------------------------------
    # Quantum Finance expansion stubs
    # ------------------------------------------------------------------

    def ensure_quantum_enabled(self) -> None:
        if not self.quantum_enabled:
            raise RuntimeError("Quantum Finance expansion is disabled. Enable it from Settings to continue.")

    def execute_swarm_trade(self, strategy: str, budget: float, leverage: float) -> MutableMapping[str, Any]:
        self.ensure_quantum_enabled()
        payload = {
            "strategy": strategy,
            "budget": budget,
            "leverage": leverage,
            "timestamp": time.time(),
        }
        self.log_event.emit("INFO", f"Simulated swarm trade: {payload}")
        return payload

    def configure_hedge(self, exposure: float, hedge_ratio: float, instrument: str) -> MutableMapping[str, Any]:
        self.ensure_quantum_enabled()
        payload = {
            "exposure": exposure,
            "hedge_ratio": hedge_ratio,
            "instrument": instrument,
            "timestamp": time.time(),
        }
        self.log_event.emit("INFO", f"Updated hedge posture: {payload}")
        return payload

    def run_csp_engine(self, depth: int, risk_limit: float) -> MutableMapping[str, Any]:
        self.ensure_quantum_enabled()
        payload = {
            "depth": depth,
            "risk_limit": risk_limit,
            "solutions": depth * 3,
            "timestamp": time.time(),
        }
        self.log_event.emit("INFO", f"CSP engine analysed {payload['solutions']} permutations")
        return payload

    def connect_defi_endpoint(self, endpoint: str, token: str) -> MutableMapping[str, Any]:
        self.ensure_quantum_enabled()
        payload = {
            "endpoint": endpoint,
            "token": token[:4] + "…" if token else "",
            "status": "connected",
            "timestamp": time.time(),
        }
        self.log_event.emit("INFO", f"Linked DeFi endpoint {endpoint}")
        return payload

    def audit_strategy(self, name: str, horizon: int) -> MutableMapping[str, Any]:
        self.ensure_quantum_enabled()
        payload = {
            "name": name,
            "horizon": horizon,
            "score": round(random.uniform(0.2, 0.95), 3),
            "timestamp": time.time(),
        }
        self.log_event.emit("INFO", f"Audit complete for strategy {name}")
        return payload

    # ------------------------------------------------------------------
    # Web3 / blockchain forensics helpers
    # ------------------------------------------------------------------

    def ensure_web3_forensics_enabled(self) -> None:
        if not self.web3_enabled:
            raise RuntimeError(
                "Web3 expansion is disabled. Enable it from Settings to access blockchain forensics."
            )

    def scan_nodes(self, network: str) -> List[str]:
        self.ensure_web3_forensics_enabled()
        nodes = [f"{network}-node-{index}" for index in range(1, 6)]
        self.log_event.emit("INFO", f"Discovered {len(nodes)} nodes on {network}")
        return nodes

    def detect_sybil_patterns(self, sensitivity: float) -> MutableMapping[str, Any]:
        self.ensure_web3_forensics_enabled()
        incidents = int(max(1, sensitivity * random.randint(1, 5)))
        payload = {"incidents": incidents, "sensitivity": sensitivity, "timestamp": time.time()}
        self.log_event.emit("INFO", f"Sybil detection flagged {incidents} patterns")
        return payload

    def perform_ghost_rpc(self, method: str, payload: str) -> MutableMapping[str, Any]:
        self.ensure_web3_forensics_enabled()
        response = {
            "method": method,
            "payload": payload,
            "status": "ok",
            "latency_ms": round(random.uniform(45, 140), 2),
        }
        self.log_event.emit("INFO", f"GhostRPC {method} completed")
        return response

    def cluster_on_chain_identities(self, depth: int) -> MutableMapping[str, Any]:
        self.ensure_web3_forensics_enabled()
        payload = {"clusters": max(1, depth // 2), "depth": depth, "timestamp": time.time()}
        self.log_event.emit("INFO", f"Identity clustering produced {payload['clusters']} clusters")
        return payload

    def generate_mycelium_map(self, hops: int) -> MutableMapping[str, Any]:
        self.ensure_web3_forensics_enabled()
        payload = {
            "nodes": hops * 4,
            "edges": hops * 6,
            "timestamp": time.time(),
        }
        self.log_event.emit("INFO", f"Mycelium visualisation ready with {payload['nodes']} nodes")
        return payload

    # ------------------------------------------------------------------
    # Phantomload helpers for specialised modules
    # ------------------------------------------------------------------

    def simulate_attack_profile(self, profile: str, duration: int) -> MutableMapping[str, Any]:
        if not self.phantom_enabled:
            raise RuntimeError("Phantomload expansion disabled. Enable it from Settings to launch simulations.")
        payload = {
            "profile": profile,
            "duration": duration,
            "events": duration * random.randint(2, 6),
        }
        self.log_event.emit("INFO", f"Attack simulation queued: {payload}")
        return payload

    def configure_stealth_profile(self, jitter: float, cover: str) -> MutableMapping[str, Any]:
        if not self.phantom_enabled:
            raise RuntimeError("Phantomload expansion disabled. Enable it from Settings to tune stealth tools.")
        payload = {"jitter": jitter, "cover": cover, "timestamp": time.time()}
        self.log_event.emit("INFO", f"Stealth envelope updated: {payload}")
        return payload

    def export_phantom_protocol(self, path: Path) -> Path:
        if not self.phantom_enabled:
            raise RuntimeError("Phantomload expansion disabled. Enable it from Settings to export protocols.")
        data = {"status": self.phantom_status(), "mesh": self.phantom_mesh_snapshot()}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.log_event.emit("INFO", f"Protocol package exported to {path}")
        return path

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def load_config(self, name: str) -> MutableMapping[str, Any]:
        loaders: Dict[str, Callable[[], MutableMapping[str, Any]]] = {
            "pipeline": lambda: DEFAULT_PIPELINE_CONFIG,
            "phosphoros_web3": load_phosphoros_web3_config,
            "phantomload": load_phantomload_config,
        }
        if name not in loaders:
            raise KeyError(f"Unknown config '{name}'")
        config = loaders[name]()
        self._last_config = config
        if name == "pipeline":
            self.pipeline_config = copy.deepcopy(config)
            self.refresh_orchestrator()
        elif name == "phantomload":
            self.apply_phantom_config(config)
        self.log_event.emit("INFO", f"Loaded {name} configuration")
        return config

    def validate_yaml(self, text: str) -> MutableMapping[str, Any]:
        config = yaml.safe_load(text) if text.strip() else {}
        if not isinstance(config, MutableMapping):
            raise ValueError("Configuration must be a mapping")
        return config

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        self.bridge_stop()
        self.phantom_kernel.stop()
        logging.getLogger(__name__).info("Controller shutdown completed")


# ---------------------------------------------------------------------------
# Base module widget
# ---------------------------------------------------------------------------


class ModuleWidget(QWidget):
    """Base widget used for individual feature modules."""

    request_notification = pyqtSignal(str, str)

    def __init__(self, controller: AppController, title: str, icon: Optional[QIcon] = None) -> None:
        super().__init__()
        self.controller = controller
        self.title = title
        self.icon = icon
        self.status = StatusIndicator()
        self.log_console = LogConsole()
        self.preview = PreviewCanvas()
        self._build_layout()
        self._connect_logging()

    # UI -----------------------------------------------------------------
    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title_label = QLabel(self.title)
        title_label.setObjectName("ModuleTitle")
        title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(self.status)
        layout.addLayout(header)
        layout.addWidget(self._create_body())
        layout.addWidget(self._create_footer())

    def _create_body(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._create_control_panel())
        preview_box = QGroupBox("Visualisation")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview)
        splitter.addWidget(preview_box)
        splitter.setSizes([350, 650])
        return splitter

    def _create_control_panel(self) -> QWidget:
        raise NotImplementedError

    def _create_footer(self) -> QWidget:
        box = QGroupBox("Module Logs")
        layout = QVBoxLayout(box)
        layout.addWidget(self.log_console)
        return box

    # Logging ------------------------------------------------------------
    def _connect_logging(self) -> None:
        handler = QtLogHandler(LogSignalEmitter())
        handler.emitter.log_record.connect(self.log_console.append_message)  # type: ignore[arg-type]
        handler.setLevel(logging.DEBUG)
        logging.getLogger(self.__class__.__name__).addHandler(handler)
        logging.getLogger(self.__class__.__name__).setLevel(logging.DEBUG)

    # Helpers ------------------------------------------------------------
    def run_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        on_success: Optional[Callable[[object], None]] = None,
        **kwargs: Any,
    ) -> None:
        worker = Worker(func, *args, **kwargs)

        def on_started() -> None:
            self.status.update_status("running")

        def on_finished(result: object) -> None:
            self.status.update_status("success")
            if on_success is not None:
                QTimer.singleShot(0, lambda: on_success(result))

        def on_error(message: str) -> None:
            self.status.update_status("error")
            self.log_console.append_message("ERROR", message)
            self.request_notification.emit("Operation failed", message)

        worker.signals.started.connect(on_started)
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        self.controller.thread_pool.start(worker)


# ---------------------------------------------------------------------------
# Core layout modules aligned with navigation schema
# ---------------------------------------------------------------------------


class DashboardModuleWidget(ModuleWidget):
    """Operational overview with quick actions and alerts."""

    def __init__(self, controller: AppController) -> None:
        self.bridge_label = QLabel("Bridge: --")
        self.pipeline_label = QLabel("Pipeline: --")
        self.seed_label = QLabel("Seeds: Expansion disabled")
        self.alerts_list = QListWidget()
        self.status_tree = QTreeWidget()
        super().__init__(controller, "Operations Dashboard")
        self.status_tree.setHeaderLabels(["Subsystem", "Value"])
        self.alerts_list.setMinimumHeight(120)
        self.alerts_list.setToolTip("Recent activity highlights")
        self._refresh_status()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_status)
        self.timer.start(2000)

    def _create_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        status_group = QGroupBox("System Status")
        status_layout = QFormLayout(status_group)
        status_layout.addRow("Bridge", self.bridge_label)
        status_layout.addRow("Pipeline", self.pipeline_label)
        status_layout.addRow("Seeds", self.seed_label)
        layout.addWidget(status_group)

        quick_group = QGroupBox("Quick Actions")
        quick_layout = QHBoxLayout(quick_group)
        start_btn = QPushButton("Start Bridge")
        start_btn.setToolTip("Start the Scorpio bridge heartbeat")
        start_btn.clicked.connect(lambda: self.run_async(self.controller.bridge_start))
        stop_btn = QPushButton("Stop Bridge")
        stop_btn.setToolTip("Stop the Scorpio bridge heartbeat")
        stop_btn.clicked.connect(lambda: self.run_async(self.controller.bridge_stop))
        pipeline_btn = QPushButton("Run Pipeline Cycle")
        pipeline_btn.setToolTip("Execute the orchestrator once")
        pipeline_btn.clicked.connect(lambda: self.run_async(self.controller.run_pipeline_cycle))
        quick_layout.addWidget(start_btn)
        quick_layout.addWidget(stop_btn)
        quick_layout.addWidget(pipeline_btn)
        layout.addWidget(quick_group)

        alerts_group = QGroupBox("Alerts & Activity")
        alerts_layout = QVBoxLayout(alerts_group)
        refresh_alerts = QPushButton("Refresh Alerts")
        refresh_alerts.setToolTip("Pull supervisor and MetaMemory highlights")
        refresh_alerts.clicked.connect(self._populate_alerts)
        alerts_layout.addWidget(refresh_alerts)
        alerts_layout.addWidget(self.alerts_list)
        layout.addWidget(alerts_group)

        status_detail = QGroupBox("Module Status")
        status_layout = QVBoxLayout(status_detail)
        self.status_tree.setToolTip("Snapshot of key subsystem metrics")
        status_layout.addWidget(self.status_tree)
        layout.addWidget(status_detail)

        layout.addStretch()
        return panel

    def _refresh_status(self) -> None:
        bridge_state = "Running" if self.controller._bridge_running else "Stopped"
        self.bridge_label.setText(bridge_state)
        seeds, clusters = self.controller.seed_counts()
        if self.controller.web3_enabled:
            self.seed_label.setText(f"{seeds} seeds / {clusters} clusters")
        else:
            self.seed_label.setText("Expansion disabled")
        last_result = self.controller.fixpunkt_last_result or {}
        if last_result:
            self.pipeline_label.setText(f"Consensus ready ({len(last_result)})")
        else:
            self.pipeline_label.setText("Idle")
        self._populate_status_tree()
        self.preview.plot_heatmap(self.controller.reverb_activity())

    def _populate_status_tree(self) -> None:
        snapshot = self.controller.supervisor_snapshot()
        self.status_tree.clear()
        for key, value in snapshot.items():
            self.status_tree.addTopLevelItem(QTreeWidgetItem([key, f"{value:.3f}"]))

    def _populate_alerts(self) -> None:
        self.alerts_list.clear()
        meta = self.controller.meta_history()[-5:]
        for entry in reversed(meta):
            self.alerts_list.addItem(json.dumps(entry))
        self.alerts_list.scrollToTop()


class DataImportModuleWidget(ModuleWidget):
    """Data onboarding tools for pointclouds and configurations."""

    def __init__(self, controller: AppController) -> None:
        self.pointcloud_path = QLineEdit()
        self.config_path = QLineEdit()
        self.seed_path = QLineEdit()
        super().__init__(controller, "Data Import")
        self.pointcloud_path.setPlaceholderText("Select CSV/JSON pointcloud file")
        self.config_path.setPlaceholderText("Select pipeline YAML file")
        self.seed_path.setPlaceholderText("Select seed phrases text file")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Import Sources")
        layout = QVBoxLayout(panel)

        point_group = QGroupBox("Pointcloud Dataset")
        point_layout = QHBoxLayout(point_group)
        browse_point = QPushButton("Browse…")
        browse_point.clicked.connect(lambda: self._select_file(self.pointcloud_path, "Data (*.csv *.json)"))
        load_point = QPushButton("Load")
        load_point.setToolTip("Load the selected pointcloud into the workspace")
        load_point.clicked.connect(self._load_pointcloud)
        point_layout.addWidget(self.pointcloud_path)
        point_layout.addWidget(browse_point)
        point_layout.addWidget(load_point)
        layout.addWidget(point_group)

        config_group = QGroupBox("Pipeline Blueprint")
        config_layout = QHBoxLayout(config_group)
        browse_config = QPushButton("Browse…")
        browse_config.clicked.connect(lambda: self._select_file(self.config_path, "YAML (*.yaml *.yml)"))
        load_config = QPushButton("Load")
        load_config.setToolTip("Load YAML and apply to the orchestrator")
        load_config.clicked.connect(self._load_config)
        config_layout.addWidget(self.config_path)
        config_layout.addWidget(browse_config)
        config_layout.addWidget(load_config)
        layout.addWidget(config_group)

        seed_group = QGroupBox("Seed Phrases")
        seed_layout = QHBoxLayout(seed_group)
        browse_seed = QPushButton("Browse…")
        browse_seed.clicked.connect(lambda: self._select_file(self.seed_path, "Text (*.txt)", multiple=False))
        import_seeds = QPushButton("Import")
        import_seeds.setToolTip("Import seed phrases line-by-line (requires Web3 expansion)")
        import_seeds.clicked.connect(self._import_seeds)
        seed_layout.addWidget(self.seed_path)
        seed_layout.addWidget(browse_seed)
        seed_layout.addWidget(import_seeds)
        layout.addWidget(seed_group)

        layout.addStretch()
        return panel

    def _select_file(self, edit: QLineEdit, pattern: str, multiple: bool = False) -> None:
        if multiple:
            paths, _ = QFileDialog.getOpenFileNames(self, "Select files", str(Path.cwd()), pattern)
            if paths:
                edit.setText(",".join(paths))
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select file", str(Path.cwd()), pattern)
            if path:
                edit.setText(path)

    def _load_pointcloud(self) -> None:
        path = self.pointcloud_path.text().strip()
        if not path:
            self.request_notification.emit("Pointcloud missing", "Select a pointcloud file to import.")
            return
        self.run_async(
            self.controller.load_pointcloud_from_file,
            Path(path),
            on_success=lambda _: self.preview.plot_pointcloud(self.controller.pointcloud),
        )

    def _load_config(self) -> None:
        path = self.config_path.text().strip()
        if not path:
            self.request_notification.emit("Config missing", "Select a YAML file to load.")
            return
        try:
            config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            self.log_console.append_message("ERROR", f"Failed to read config: {exc}")
            self.request_notification.emit("Import failed", str(exc))
            return
        if not isinstance(config, MutableMapping):
            self.request_notification.emit("Invalid config", "Configuration must be a mapping.")
            return
        self.controller.apply_pipeline_blueprint(config)
        self.log_console.append_message("INFO", f"Pipeline blueprint applied from {path}")

    def _import_seeds(self) -> None:
        if not self.controller.web3_enabled:
            self.request_notification.emit(
                "Web3 disabled",
                "Enable the Web3 expansion to import seed phrases.",
            )
            return
        path = self.seed_path.text().strip()
        if not path:
            self.request_notification.emit("Seed file missing", "Select a seed phrase file.")
            return
        phrases = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        for phrase in phrases:
            self.run_async(self.controller.add_seed_phrase, phrase, False)
        self.log_console.append_message("INFO", f"Queued {len(phrases)} seed phrase(s) for import")


class MutationEngineModuleWidget(ModuleWidget):
    """Mutation workflows built on the Seed DNA engine."""

    def __init__(self, controller: AppController) -> None:
        self.seed_input = QLineEdit()
        self.mutate_toggle = QCheckBox("Mutate on ingest")
        self.batch_spin = QSpinBox()
        super().__init__(controller, "Mutation Engine")
        self.seed_input.setPlaceholderText("Seed phrase or entropy source")
        self.mutate_toggle.setChecked(True)
        self.batch_spin.setRange(1, 10)
        self.batch_spin.setValue(1)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Mutation Controls")
        layout = QFormLayout(panel)
        layout.addRow("Seed", self.seed_input)
        layout.addRow("Batches", self.batch_spin)
        layout.addRow("Options", self.mutate_toggle)
        ingest_btn = QPushButton("Encode Seed")
        ingest_btn.setToolTip("Encode the provided seed phrase")
        ingest_btn.clicked.connect(self._ingest_seed)
        cluster_btn = QPushButton("Cluster Seeds")
        cluster_btn.setToolTip("Organise seeds into clusters")
        cluster_btn.clicked.connect(lambda: self.run_async(self.controller.cluster_seeds))
        layout.addRow(ingest_btn)
        layout.addRow(cluster_btn)
        if not self.controller.web3_enabled:
            info = QLabel("Enable the Web3 expansion in Settings to operate the mutation engine.")
            info.setWordWrap(True)
            layout.addRow(info)
            ingest_btn.setEnabled(False)
            cluster_btn.setEnabled(False)
        return panel

    def _ingest_seed(self) -> None:
        if not self.controller.web3_enabled:
            self.request_notification.emit(
                "Web3 disabled",
                "Enable the Web3 expansion to operate the mutation engine.",
            )
            return
        phrase = self.seed_input.text().strip()
        if not phrase:
            self.request_notification.emit("Seed missing", "Provide a seed phrase to encode.")
            return
        batches = self.batch_spin.value()

        def worker() -> List[float]:
            geometry: List[float] = []
            for _ in range(batches):
                geometry = self.controller.add_seed_phrase(phrase, mutate=self.mutate_toggle.isChecked())
            return geometry

        self.run_async(
            worker,
            on_success=lambda geo: self.log_console.append_message(
                "INFO", f"Encoded seed • last vector length {len(geo)}"
            ),
        )


class SpectralScannerModuleWidget(ModuleWidget):
    """Analyser for resonance spectra derived from ReverbRing logs."""

    def __init__(self, controller: AppController) -> None:
        self.window_spin = QSpinBox()
        super().__init__(controller, "Spectral Scanner")
        self.window_spin.setRange(5, 200)
        self.window_spin.setValue(40)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_view)
        self.timer.start(2500)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Scanner Controls")
        layout = QFormLayout(panel)
        layout.addRow("Window", self.window_spin)
        capture_btn = QPushButton("Capture Spectrum")
        capture_btn.setToolTip("Sample recent resonance readings and plot them")
        capture_btn.clicked.connect(self._refresh_view)
        layout.addRow(capture_btn)
        return panel

    def _refresh_view(self) -> None:
        data = self.controller.reverb_activity()[-self.window_spin.value():]
        if not data:
            self.log_console.append_message("INFO", "No spectral data available yet")
            return
        energy = [entry.get("seed", 0.0) for entry in data]
        self.preview.plot_series(energy, title="Resonance Energy", ylabel="Amplitude")
        self.log_console.append_message("DEBUG", f"Captured {len(energy)} resonance samples")


class AttackSimulationModuleWidget(ModuleWidget):
    """Phantomload attack simulation console."""

    def __init__(self, controller: AppController) -> None:
        self.profile_combo = QComboBox()
        self.duration_spin = QSpinBox()
        super().__init__(controller, "Attack Sim")
        self.profile_combo.addItems(["burst", "sustained", "waveform"])
        self.duration_spin.setRange(1, 600)
        self.duration_spin.setValue(60)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Simulation")
        layout = QFormLayout(panel)
        layout.addRow("Profile", self.profile_combo)
        layout.addRow("Duration (s)", self.duration_spin)
        launch_btn = QPushButton("Queue Simulation")
        launch_btn.setToolTip("Run the phantomload attack simulation")
        launch_btn.clicked.connect(self._launch_sim)
        layout.addRow(launch_btn)
        return panel

    def _launch_sim(self) -> None:
        self.run_async(
            self.controller.simulate_attack_profile,
            self.profile_combo.currentText(),
            self.duration_spin.value(),
        )


class StealthToolsModuleWidget(ModuleWidget):
    """Controls for phantomload stealth envelopes and proxies."""

    def __init__(self, controller: AppController) -> None:
        self.jitter_spin = QDoubleSpinBox()
        self.cover_combo = QComboBox()
        self.proxy_input = QTextEdit()
        super().__init__(controller, "Stealth Tools")
        self.jitter_spin.setRange(0.0, 5.0)
        self.jitter_spin.setSingleStep(0.1)
        self.jitter_spin.setValue(0.5)
        self.cover_combo.addItems(["tls", "http", "custom"])
        self.proxy_input.setPlaceholderText("Proxy endpoints, one per line")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Stealth Configuration")
        layout = QVBoxLayout(panel)
        form = QFormLayout()
        form.addRow("Jitter", self.jitter_spin)
        form.addRow("Cover", self.cover_combo)
        layout.addLayout(form)
        proxy_group = QGroupBox("Proxy Pool")
        proxy_layout = QVBoxLayout(proxy_group)
        proxy_layout.addWidget(self.proxy_input)
        apply_btn = QPushButton("Apply Stealth Profile")
        apply_btn.setToolTip("Update phantomload stealth and proxy pool")
        apply_btn.clicked.connect(self._apply)
        proxy_layout.addWidget(apply_btn)
        layout.addWidget(proxy_group)
        return panel

    def _apply(self) -> None:
        self.run_async(
            self.controller.configure_stealth_profile,
            float(self.jitter_spin.value()),
            self.cover_combo.currentText(),
        )
        proxies = [line.strip() for line in self.proxy_input.toPlainText().splitlines() if line.strip()]
        if proxies:
            self.run_async(self.controller.phantom_update_proxies, proxies, self.cover_combo.currentText())


class PhantomExportModuleWidget(ModuleWidget):
    """Exports phantomload telemetry and protocols."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Export / Protocol")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Exports")
        layout = QVBoxLayout(panel)
        export_protocol = QPushButton("Export Protocol Package…")
        export_protocol.setToolTip("Export phantomload status and mesh snapshot")
        export_protocol.clicked.connect(self._export_protocol)
        export_mesh = QPushButton("Export Traffic Mesh…")
        export_mesh.setToolTip("Export the current phantomload mesh")
        export_mesh.clicked.connect(self._export_mesh)
        layout.addWidget(export_protocol)
        layout.addWidget(export_mesh)
        layout.addStretch()
        return panel

    def _export_protocol(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export protocol", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        self.run_async(self.controller.export_phantom_protocol, Path(path))

    def _export_mesh(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export mesh", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        self.run_async(self.controller.export_phantom_mesh, Path(path))


class SwarmTradingModuleWidget(ModuleWidget):
    """Quantum Finance swarm trading console."""

    def __init__(self, controller: AppController) -> None:
        self.strategy_input = QLineEdit()
        self.budget_spin = QDoubleSpinBox()
        self.leverage_spin = QDoubleSpinBox()
        super().__init__(controller, "Swarm Trading")
        self.budget_spin.setRange(0.0, 10_000_000.0)
        self.budget_spin.setPrefix("$")
        self.budget_spin.setValue(10000.0)
        self.leverage_spin.setRange(1.0, 50.0)
        self.leverage_spin.setValue(5.0)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Trade Parameters")
        layout = QFormLayout(panel)
        layout.addRow("Strategy", self.strategy_input)
        layout.addRow("Budget", self.budget_spin)
        layout.addRow("Leverage", self.leverage_spin)
        execute_btn = QPushButton("Execute Simulation")
        execute_btn.setToolTip("Simulate a swarm trade execution")
        execute_btn.clicked.connect(self._execute)
        layout.addRow(execute_btn)
        return panel

    def _execute(self) -> None:
        self.run_async(
            self.controller.execute_swarm_trade,
            self.strategy_input.text() or "default",
            float(self.budget_spin.value()),
            float(self.leverage_spin.value()),
        )


class HedgeControlsModuleWidget(ModuleWidget):
    """Risk hedging controls for Quantum Finance."""

    def __init__(self, controller: AppController) -> None:
        self.exposure_spin = QDoubleSpinBox()
        self.hedge_spin = QDoubleSpinBox()
        self.instrument_combo = QComboBox()
        super().__init__(controller, "Hedge Controls")
        self.exposure_spin.setRange(-1_000_000.0, 1_000_000.0)
        self.exposure_spin.setPrefix("$")
        self.hedge_spin.setRange(0.0, 2.0)
        self.hedge_spin.setSingleStep(0.05)
        self.hedge_spin.setValue(0.5)
        self.instrument_combo.addItems(["options", "futures", "synthetic"])

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Hedge Settings")
        layout = QFormLayout(panel)
        layout.addRow("Exposure", self.exposure_spin)
        layout.addRow("Hedge Ratio", self.hedge_spin)
        layout.addRow("Instrument", self.instrument_combo)
        apply_btn = QPushButton("Apply Hedge")
        apply_btn.setToolTip("Apply the hedge configuration")
        apply_btn.clicked.connect(self._apply)
        layout.addRow(apply_btn)
        return panel

    def _apply(self) -> None:
        self.run_async(
            self.controller.configure_hedge,
            float(self.exposure_spin.value()),
            float(self.hedge_spin.value()),
            self.instrument_combo.currentText(),
        )


class CspEngineModuleWidget(ModuleWidget):
    """Constraint solving playground for Quantum Finance."""

    def __init__(self, controller: AppController) -> None:
        self.depth_spin = QSpinBox()
        self.risk_spin = QDoubleSpinBox()
        super().__init__(controller, "CSP Engine")
        self.depth_spin.setRange(1, 500)
        self.depth_spin.setValue(50)
        self.risk_spin.setRange(0.0, 1.0)
        self.risk_spin.setSingleStep(0.05)
        self.risk_spin.setValue(0.35)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Engine Parameters")
        layout = QFormLayout(panel)
        layout.addRow("Depth", self.depth_spin)
        layout.addRow("Risk Limit", self.risk_spin)
        run_btn = QPushButton("Run Analysis")
        run_btn.setToolTip("Execute the CSP engine")
        run_btn.clicked.connect(self._run)
        layout.addRow(run_btn)
        return panel

    def _run(self) -> None:
        self.run_async(
            self.controller.run_csp_engine,
            self.depth_spin.value(),
            float(self.risk_spin.value()),
        )


class DefiConnectorModuleWidget(ModuleWidget):
    """Connector management for DeFi endpoints."""

    def __init__(self, controller: AppController) -> None:
        self.endpoint_input = QLineEdit()
        self.token_input = QLineEdit()
        super().__init__(controller, "DeFi Connector")
        self.endpoint_input.setPlaceholderText("https://node.example")
        self.token_input.setPlaceholderText("Token or credential")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Connector")
        layout = QFormLayout(panel)
        layout.addRow("Endpoint", self.endpoint_input)
        layout.addRow("Token", self.token_input)
        link_btn = QPushButton("Link Endpoint")
        link_btn.setToolTip("Link the DeFi endpoint (simulated)")
        link_btn.clicked.connect(self._link)
        layout.addRow(link_btn)
        return panel

    def _link(self) -> None:
        self.run_async(
            self.controller.connect_defi_endpoint,
            self.endpoint_input.text(),
            self.token_input.text(),
        )


class StrategyAuditModuleWidget(ModuleWidget):
    """Audit and compliance scoring for Quantum Finance strategies."""

    def __init__(self, controller: AppController) -> None:
        self.strategy_input = QLineEdit()
        self.horizon_spin = QSpinBox()
        super().__init__(controller, "Strategies / Audit")
        self.strategy_input.setPlaceholderText("Strategy name")
        self.horizon_spin.setRange(1, 365)
        self.horizon_spin.setValue(30)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Audit")
        layout = QFormLayout(panel)
        layout.addRow("Strategy", self.strategy_input)
        layout.addRow("Horizon (days)", self.horizon_spin)
        audit_btn = QPushButton("Run Audit")
        audit_btn.setToolTip("Simulate a compliance audit")
        audit_btn.clicked.connect(self._audit)
        layout.addRow(audit_btn)
        return panel

    def _audit(self) -> None:
        self.run_async(
            self.controller.audit_strategy,
            self.strategy_input.text() or "default",
            self.horizon_spin.value(),
        )


class NodeScannerModuleWidget(ModuleWidget):
    """Blockchain node discovery."""

    def __init__(self, controller: AppController) -> None:
        self.network_input = QLineEdit()
        super().__init__(controller, "Node Scanner")
        self.network_input.setPlaceholderText("Network name, e.g. ethereum")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Scanner")
        layout = QFormLayout(panel)
        layout.addRow("Network", self.network_input)
        scan_btn = QPushButton("Scan")
        scan_btn.setToolTip("Discover nodes on the specified network")
        scan_btn.clicked.connect(self._scan)
        layout.addRow(scan_btn)
        return panel

    def _scan(self) -> None:
        self.run_async(self.controller.scan_nodes, self.network_input.text() or "default")


class SybilDetectionModuleWidget(ModuleWidget):
    """Sybil pattern detection controls."""

    def __init__(self, controller: AppController) -> None:
        self.sensitivity_spin = QDoubleSpinBox()
        super().__init__(controller, "Sybil Detection")
        self.sensitivity_spin.setRange(0.1, 2.0)
        self.sensitivity_spin.setSingleStep(0.1)
        self.sensitivity_spin.setValue(0.8)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Detection")
        layout = QFormLayout(panel)
        layout.addRow("Sensitivity", self.sensitivity_spin)
        detect_btn = QPushButton("Run Detection")
        detect_btn.setToolTip("Run Sybil detection against cached graphs")
        detect_btn.clicked.connect(self._detect)
        layout.addRow(detect_btn)
        return panel

    def _detect(self) -> None:
        self.run_async(self.controller.detect_sybil_patterns, float(self.sensitivity_spin.value()))


class GhostRpcModuleWidget(ModuleWidget):
    """GhostRPC request console."""

    def __init__(self, controller: AppController) -> None:
        self.method_input = QLineEdit()
        self.payload_edit = QTextEdit()
        super().__init__(controller, "GhostRPC")
        self.method_input.setPlaceholderText("Method name")
        self.payload_edit.setPlaceholderText("JSON payload")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("RPC Call")
        layout = QFormLayout(panel)
        layout.addRow("Method", self.method_input)
        layout.addRow("Payload", self.payload_edit)
        call_btn = QPushButton("Invoke")
        call_btn.setToolTip("Invoke the GhostRPC endpoint")
        call_btn.clicked.connect(self._call)
        layout.addRow(call_btn)
        return panel

    def _call(self) -> None:
        self.run_async(
            self.controller.perform_ghost_rpc,
            self.method_input.text() or "status",
            self.payload_edit.toPlainText(),
        )


class IdentityClusteringModuleWidget(ModuleWidget):
    """Identity clustering orchestrator."""

    def __init__(self, controller: AppController) -> None:
        self.depth_spin = QSpinBox()
        super().__init__(controller, "Identity Clustering")
        self.depth_spin.setRange(2, 200)
        self.depth_spin.setValue(20)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Clustering")
        layout = QFormLayout(panel)
        layout.addRow("Depth", self.depth_spin)
        run_btn = QPushButton("Cluster")
        run_btn.setToolTip("Cluster on-chain identities")
        run_btn.clicked.connect(self._cluster)
        layout.addRow(run_btn)
        return panel

    def _cluster(self) -> None:
        self.run_async(self.controller.cluster_on_chain_identities, self.depth_spin.value())


class MyceliumVisualizationModuleWidget(ModuleWidget):
    """Mycelium network visualisation controls."""

    def __init__(self, controller: AppController) -> None:
        self.hops_spin = QSpinBox()
        super().__init__(controller, "Mycelium Visualization")
        self.hops_spin.setRange(1, 50)
        self.hops_spin.setValue(5)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Visualization")
        layout = QFormLayout(panel)
        layout.addRow("Hops", self.hops_spin)
        render_btn = QPushButton("Render")
        render_btn.setToolTip("Render mycelium graph metrics")
        render_btn.clicked.connect(self._render)
        layout.addRow(render_btn)
        return panel

    def _render(self) -> None:
        self.run_async(self.controller.generate_mycelium_map, self.hops_spin.value())


class ProfilesModuleWidget(ModuleWidget):
    """Profile management for operator presets."""

    def __init__(self, controller: AppController) -> None:
        self.profile_name = QLineEdit()
        self.profile_notes = QTextEdit()
        super().__init__(controller, "Profiles")
        self.profile_notes.setPlaceholderText("Describe the preset or deployment context")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Profile Editor")
        layout = QFormLayout(panel)
        layout.addRow("Name", self.profile_name)
        layout.addRow("Notes", self.profile_notes)
        save_btn = QPushButton("Save Profile")
        save_btn.setToolTip("Persist the profile locally (mock)")
        save_btn.clicked.connect(self._save)
        layout.addRow(save_btn)
        return panel

    def _save(self) -> None:
        record = {
            "name": self.profile_name.text() or "untitled",
            "notes": self.profile_notes.toPlainText(),
        }
        path = Path.cwd() / "profiles"
        path.mkdir(exist_ok=True)
        file_path = path / f"{record['name'].replace(' ', '_')}.json"
        file_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        self.log_console.append_message("INFO", f"Profile saved to {file_path}")


class LicensingModuleWidget(ModuleWidget):
    """Licensing and API credentials."""

    def __init__(self, controller: AppController) -> None:
        self.license_input = QLineEdit()
        self.api_token_input = QLineEdit()
        super().__init__(controller, "Licensing & API")
        self.license_input.setPlaceholderText("License key")
        self.api_token_input.setPlaceholderText("API token for external services")
        self.api_token_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Credentials")
        layout = QFormLayout(panel)
        layout.addRow("License", self.license_input)
        layout.addRow("API Token", self.api_token_input)
        apply_btn = QPushButton("Store Credentials")
        apply_btn.setToolTip("Store credentials locally (mock)")
        apply_btn.clicked.connect(self._store)
        layout.addRow(apply_btn)
        return panel

    def _store(self) -> None:
        Path("credentials").mkdir(exist_ok=True)
        data = {
            "license": self.license_input.text(),
            "api_token": self.api_token_input.text(),
        }
        target = Path("credentials") / "licensing.json"
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.log_console.append_message("INFO", f"Credentials cached at {target}")


class IntegrationModuleWidget(ModuleWidget):
    """Integration management for external systems."""

    def __init__(self, controller: AppController) -> None:
        self.integration_list = QListWidget()
        self.endpoint_input = QLineEdit()
        super().__init__(controller, "Integration Hub")
        self.integration_list.addItems(["ShadowGraph", "Unity", "Analytics Bus"])
        self.endpoint_input.setPlaceholderText("Integration endpoint")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Integrations")
        layout = QVBoxLayout(panel)
        layout.addWidget(self.integration_list)
        form = QFormLayout()
        form.addRow("Endpoint", self.endpoint_input)
        layout.addLayout(form)
        apply_btn = QPushButton("Register Integration")
        apply_btn.setToolTip("Register or update an integration endpoint")
        apply_btn.clicked.connect(self._register)
        layout.addWidget(apply_btn)
        return panel

    def _register(self) -> None:
        selection = self.integration_list.currentItem().text() if self.integration_list.currentItem() else "custom"
        endpoint = self.endpoint_input.text()
        record = {"integration": selection, "endpoint": endpoint, "timestamp": time.time()}
        self.log_console.append_message("INFO", f"Integration updated: {record}")


class ManualModuleWidget(ModuleWidget):
    """Static manual viewer."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Manual")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Manual")
        layout = QVBoxLayout(panel)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            """AinSOFT Manual\n\n"
            "- Use the navigation sidebar to access each subsystem.\n"
            "- Dashboard provides live status and quick actions.\n"
            "- Exploration modules let you load data, inspect seeds, and export results.\n"
            "- Orchestration modules drive pipelines, mutation, meta memory, and bridge sync.\n"
            "- Expansion packs extend capabilities for specialised domains."""
        )
        layout.addWidget(text)
        return panel


class OnboardingModuleWidget(ModuleWidget):
    """Onboarding checklist and helper resources."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Onboarding")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Onboarding Checklist")
        layout = QVBoxLayout(panel)
        checklist = QListWidget()
        checklist.addItems(
            [
                "Review dashboard metrics",
                "Import sample data",
                "Configure pipeline",
                "Launch resonance sweep",
                "Review exports",
            ]
        )
        layout.addWidget(checklist)
        return panel


class FaqSupportModuleWidget(ModuleWidget):
    """FAQ and support contacts."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "FAQ & Support")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Support")
        layout = QVBoxLayout(panel)
        faq = QTextEdit()
        faq.setReadOnly(True)
        faq.setPlainText(
            """Frequently Asked Questions\n\n"
            "Q: How do I enable expansion packs?\n"
            "A: Open Settings and toggle the desired pack.\n\n"
            "Q: Where are exports stored?\n"
            "A: CSV/JSON exports are stored under the project's exports/ directory."""
        )
        layout.addWidget(faq)
        return panel


# ---------------------------------------------------------------------------
# Target acquisition module
# ---------------------------------------------------------------------------


class TargetAcquisitionModuleWidget(ModuleWidget):
    """Interactive console for directing resonance cycles at specific targets."""

    def __init__(self, controller: AppController) -> None:
        self.target_input = QLineEdit()
        self.port_spin = QSpinBox()
        self.cycle_spin = QSpinBox()
        self.proxy_enabled = QCheckBox("Use Proxy Relay")
        self.proxy_host = QLineEdit()
        self.proxy_port = QSpinBox()
        self.proxy_user = QLineEdit()
        self.proxy_pass = QLineEdit()
        self.history_list = QListWidget()
        super().__init__(controller, "Target Acquisition Console")
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(8080)
        self.cycle_spin.setRange(1, 50)
        self.cycle_spin.setValue(3)
        self.proxy_port.setRange(0, 65535)
        self.proxy_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.target_input.setPlaceholderText("e.g. 203.0.113.5 or gateway.example")
        self.target_input.setToolTip("Hostname or IP address to engage")
        self.port_spin.setToolTip("Destination port for resonance cycles")
        self.cycle_spin.setToolTip("Number of resonance cycles to execute")
        self.proxy_host.setPlaceholderText("proxy host (optional)")
        self.proxy_user.setPlaceholderText("username (optional)")
        self.proxy_pass.setPlaceholderText("password (optional)")
        self.history_list.setToolTip("Recent resonance engagements")
        self.history_list.setMinimumHeight(160)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_history)
        self.refresh_timer.start(5000)
        QTimer.singleShot(0, self._refresh_history)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Engagement Controls")
        layout = QVBoxLayout(panel)

        target_group = QGroupBox("Target Selection")
        target_form = QFormLayout(target_group)
        target_form.addRow("Target", self.target_input)
        target_form.addRow("Port", self.port_spin)
        target_form.addRow("Cycles", self.cycle_spin)
        engage_btn = QPushButton("Engage Resonance Sweep")
        engage_btn.setToolTip("Execute resonance cycles against the chosen target")
        engage_btn.clicked.connect(self._engage_target)
        target_form.addRow(engage_btn)
        layout.addWidget(target_group)

        proxy_group = QGroupBox("Proxy Relay")
        proxy_form = QFormLayout(proxy_group)
        proxy_form.addRow(self.proxy_enabled)
        proxy_form.addRow("Host", self.proxy_host)
        proxy_form.addRow("Port", self.proxy_port)
        proxy_form.addRow("Username", self.proxy_user)
        proxy_form.addRow("Password", self.proxy_pass)
        apply_proxy_btn = QPushButton("Arm Proxy Defaults")
        apply_proxy_btn.setToolTip("Store proxy routing defaults for future resonance cycles")
        apply_proxy_btn.clicked.connect(self._apply_proxy_defaults)
        proxy_form.addRow(apply_proxy_btn)
        layout.addWidget(proxy_group)

        history_group = QGroupBox("Engagement History")
        history_layout = QVBoxLayout(history_group)
        history_layout.addWidget(self.history_list)
        layout.addWidget(history_group)

        layout.addStretch()
        return panel

    def _engage_target(self) -> None:
        target = self.target_input.text().strip()
        if not target:
            self.log_console.append_message("ERROR", "Target is required before launching a sweep")
            self.request_notification.emit("Target missing", "Provide a hostname or IP address to engage.")
            return
        proxy_config = self._collect_proxy_overrides()
        self.run_async(
            self.controller.run_resonance_cycles,
            target,
            self.port_spin.value(),
            self.cycle_spin.value(),
            proxy_config,
            on_success=self._on_cycle_complete,
        )

    def _collect_proxy_overrides(self) -> Mapping[str, Any]:
        return {
            "enabled": self.proxy_enabled.isChecked(),
            "host": self.proxy_host.text() or None,
            "port": self.proxy_port.value() or None,
            "username": self.proxy_user.text() or None,
            "password": self.proxy_pass.text() or None,
        }

    def _apply_proxy_defaults(self) -> None:
        config = self._collect_proxy_overrides()
        self.controller.set_lifecycle_proxy(config)
        self.log_console.append_message("INFO", "Proxy defaults primed for resonance sweeps")

    def _on_cycle_complete(self, summary: MutableMapping[str, Any]) -> None:
        message = (
            f"Target {summary.get('target')}:{summary.get('port')} • {summary.get('cycles')} cycle(s)"
            f" in {summary.get('total_duration', 0.0):.2f}s"
        )
        self.log_console.append_message("INFO", message)
        self.history_list.insertItem(0, message)
        durations = [float(item.get("duration", 0.0)) for item in summary.get("timeline", [])]
        if durations:
            self.preview.plot_series(durations, title="Cycle Duration", ylabel="Seconds")

    def _refresh_history(self) -> None:
        history = list(reversed(self.controller.resonance_history()[-8:]))
        self.history_list.clear()
        for entry in history:
            text = (
                f"{entry.get('target')}:{entry.get('port')} • {entry.get('cycles')} cycle(s)"
                f" • {entry.get('total_duration', 0.0):.2f}s"
            )
            self.history_list.addItem(text)
        durations = self.controller.resonance_metrics()
        if durations:
            self.preview.plot_series(durations, title="Cycle Duration", ylabel="Seconds")


# ---------------------------------------------------------------------------
# MeshLayer module
# ---------------------------------------------------------------------------


class MeshLayerModuleWidget(ModuleWidget):
    """MeshLayer control surface with audit and export tooling."""

    def __init__(self, controller: AppController) -> None:
        self.mode_combo: Optional[QComboBox] = None
        self.k_spin: Optional[QSpinBox] = None
        self.threshold_slider: Optional[QSlider] = None
        super().__init__(controller, "3D Mesh Viewer")

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Mesh Controls")
        layout = QVBoxLayout(panel)

        point_section = QGroupBox("PointCloud")
        point_layout = QFormLayout(point_section)
        count_spin = QSpinBox()
        count_spin.setRange(10, 10000)
        count_spin.setValue(128)
        count_spin.setToolTip("Number of points to synthesise for the mesh")
        dim_spin = QSpinBox()
        dim_spin.setRange(2, 10)
        dim_spin.setValue(5)
        dim_spin.setToolTip("Dimensionality of the pointcloud")
        generate_btn = QPushButton("Synthesize Sensor Points")
        generate_btn.setToolTip("Generate a synthetic pointcloud for the resonance field")
        generate_btn.clicked.connect(
            lambda: self._handle_generate_pointcloud(count_spin.value(), dim_spin.value())
        )
        load_btn = QPushButton("Load External Dataset…")
        load_btn.setToolTip("Load pointcloud data from external JSON/CSV sources")
        load_btn.clicked.connect(self._handle_load_pointcloud)
        point_layout.addRow("Points", count_spin)
        point_layout.addRow("Dimensions", dim_spin)
        point_layout.addRow(generate_btn, load_btn)
        layout.addWidget(point_section)

        mesh_section = QGroupBox("Mesh Build")
        mesh_form = QFormLayout(mesh_section)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["knn", "delaunay"])
        self.mode_combo.setToolTip("Mesh construction mode")
        self.k_spin = QSpinBox()
        self.k_spin.setRange(1, 64)
        self.k_spin.setValue(5)
        self.k_spin.setToolTip("Neighbourhood size for k-NN meshes")
        build_btn = QPushButton("Forge Mesh Network")
        build_btn.setToolTip("Construct a new mesh from the active pointcloud")
        build_btn.clicked.connect(self._handle_build_mesh)
        mesh_form.addRow("Mode", self.mode_combo)
        mesh_form.addRow("k", self.k_spin)
        mesh_form.addRow(build_btn)
        layout.addWidget(mesh_section)

        ops_section = QGroupBox("Operators")
        ops_layout = QVBoxLayout(ops_section)
        weight_btn = QPushButton("Calibrate Edge Weights")
        weight_btn.setToolTip("Apply example resonance scoring to mesh edges")
        weight_btn.clicked.connect(
            lambda: self.run_async(
                self.controller.weight_mesh_edges,
                on_success=lambda _: self._refresh_mesh_preview(),
            )
        )
        solve_btn = QPushButton("Stabilize Resonance Mesh")
        solve_btn.setToolTip("Execute the solve operator to stabilise the mesh")
        solve_btn.clicked.connect(lambda: self.run_async(self.controller.solve_mesh))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(10, 90)
        self.threshold_slider.setValue(50)
        self.threshold_slider.setToolTip("Gate threshold in percent")
        gate_btn = QPushButton("Activate Gate Shield")
        gate_btn.setToolTip("Apply the gate operator using the selected threshold")
        gate_btn.clicked.connect(self._handle_gate_mesh)
        coagula_btn = QPushButton("Compact Cluster Matrix")
        coagula_btn.setToolTip("Run the coagula clustering operator")
        coagula_btn.clicked.connect(
            lambda: self.run_async(
                self.controller.coagula_mesh,
                on_success=self._on_coagula_complete,
            )
        )
        expand_btn = QPushButton("Expand Frontier")
        expand_btn.setToolTip("Expand the mesh along gradient vectors")
        expand_btn.clicked.connect(
            lambda: self.run_async(
                self.controller.expand_mesh,
                0.05,
                on_success=lambda _: self._refresh_mesh_preview(),
            )
        )
        audit_btn = QPushButton("Review Audit Trail")
        audit_btn.setToolTip("Show recent mesh audit events")
        audit_btn.clicked.connect(
            lambda: self.run_async(
                self.controller.audit_mesh,
                on_success=self._on_audit_complete,
            )
        )
        ops_layout.addWidget(weight_btn)
        ops_layout.addWidget(solve_btn)
        ops_layout.addWidget(self.threshold_slider)
        ops_layout.addWidget(gate_btn)
        ops_layout.addWidget(coagula_btn)
        ops_layout.addWidget(expand_btn)
        ops_layout.addWidget(audit_btn)
        layout.addWidget(ops_section)

        export_section = QGroupBox("Import / Export")
        export_layout = QVBoxLayout(export_section)
        export_btn = QPushButton("Deliver Mesh Blueprint…")
        export_btn.setToolTip("Export mesh as JSON for Unity pipelines")
        export_btn.clicked.connect(self._handle_export_mesh)
        import_btn = QPushButton("Restore Mesh Archive…")
        import_btn.setToolTip("Import a pickled MeshLayer state")
        import_btn.clicked.connect(self._handle_import_mesh)
        export_layout.addWidget(export_btn)
        export_layout.addWidget(import_btn)
        layout.addWidget(export_section)

        layout.addStretch()
        return panel

    # Handlers ----------------------------------------------------------
    def _handle_generate_pointcloud(self, count: int, dim: int) -> None:
        self.run_async(
            self.controller.generate_pointcloud,
            count,
            dim,
            on_success=lambda _: self.preview.plot_pointcloud(self.controller.pointcloud),
        )

    def _handle_load_pointcloud(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load pointcloud", str(Path.cwd()), "Data (*.json *.csv)")
        if not path:
            return

        self.run_async(
            self.controller.load_pointcloud_from_file,
            Path(path),
            on_success=lambda _: self.preview.plot_pointcloud(self.controller.pointcloud),
        )

    def _handle_build_mesh(self) -> None:
        mode = self.mode_combo.currentText() if self.mode_combo else "knn"
        k_value = self.k_spin.value() if self.k_spin else 5

        self.run_async(
            self.controller.build_meshlayer,
            mode,
            k_value,
            on_success=lambda _: self._refresh_mesh_preview(),
        )

    def _handle_gate_mesh(self) -> None:
        threshold = (self.threshold_slider.value() if self.threshold_slider else 50) / 100.0
        self.run_async(
            self.controller.gate_mesh,
            threshold,
            on_success=lambda _: self._refresh_mesh_preview(),
        )

    def _handle_export_mesh(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export mesh", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        self.run_async(self.controller.export_mesh, Path(path))

    def _handle_import_mesh(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import mesh state", str(Path.cwd()), "Pickle (*.pkl)")
        if not path:
            return
        self.run_async(
            self.controller.import_mesh,
            Path(path),
            on_success=lambda _: self._refresh_mesh_preview(),
        )

    def _refresh_mesh_preview(self) -> None:
        if self.controller.meshlayer:
            self.preview.plot_mesh_edges(self.controller.meshlayer)

    def _on_coagula_complete(self, result: object) -> None:
        self.log_console.append_message("INFO", f"Clusters: {result}")
        self._refresh_mesh_preview()

    def _on_audit_complete(self, events: object) -> None:
        for entry in list(events)[-10:]:
            self.log_console.append_message("DEBUG", str(entry))


# ---------------------------------------------------------------------------
# PointCloud module
# ---------------------------------------------------------------------------


class PointCloudModuleWidget(ModuleWidget):
    """PointCloud diagnostics and targeting helpers."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Cluster Map")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_preview)
        self.timer.start(3000)

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("PointCloud Inspector")
        layout = QVBoxLayout(box)
        stats_btn = QPushButton("Reveal Pointcloud Metrics")
        stats_btn.setToolTip("Display basic pointcloud statistics")
        stats_btn.clicked.connect(self._show_stats)
        targeting_btn = QPushButton("Select Prime Target")
        targeting_btn.setToolTip("Run the example targeting function")
        targeting_btn.clicked.connect(self._find_target_node)
        export_btn = QPushButton("Share Pointcloud CSV…")
        export_btn.setToolTip("Export pointcloud coordinates to CSV")
        export_btn.clicked.connect(self._export_pointcloud)
        layout.addWidget(stats_btn)
        layout.addWidget(targeting_btn)
        layout.addWidget(export_btn)
        layout.addStretch()
        return box

    def _refresh_preview(self) -> None:
        self.preview.plot_pointcloud(self.controller.pointcloud)

    def _show_stats(self) -> None:
        points = self.controller.pointcloud.as_array()
        count = len(points)
        dims = len(points[0]) if count and isinstance(points, list) else getattr(points, "shape", (0, 0))[1]
        self.log_console.append_message("INFO", f"PointCloud stats → count={count}, dimensions={dims}")
        self.preview.plot_pointcloud(self.controller.pointcloud)

    def _find_target_node(self) -> None:
        if not self.controller.meshlayer:
            self.log_console.append_message("WARNING", "Build the mesh to enable targeting")
            return
        result = self.controller.meshlayer.find_targets(example_targeting_func)
        self.log_console.append_message("INFO", f"Target node index: {result}")

    def _export_pointcloud(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export pointcloud", str(Path.cwd()), "CSV (*.csv)")
        if not path:
            return
        points = self.controller.pointcloud.as_array()
        with open(path, "w", encoding="utf-8") as handle:
            for row in points:
                handle.write(",".join(str(value) for value in row) + "\n")
        self.log_console.append_message("INFO", f"Pointcloud exported to {path}")


# ---------------------------------------------------------------------------
# Web3 suite modules (Bridge, Seed DNA, Mutation, Cells, MetaMemory, Supervisor)
# ---------------------------------------------------------------------------


class BridgeModuleWidget(ModuleWidget):
    """Controls for the ScorpioBridge heartbeat scheduler."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Scorpio Bridge / Sync")

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Heartbeat")
        layout = QVBoxLayout(box)
        start_btn = QPushButton("Engage Bridge Heartbeat")
        start_btn.setToolTip("Start the ScorpioBridge heartbeat thread")
        start_btn.clicked.connect(lambda: self.run_async(self.controller.bridge_start))
        stop_btn = QPushButton("Disengage Bridge Link")
        stop_btn.setToolTip("Stop the ScorpioBridge heartbeat thread")
        stop_btn.clicked.connect(lambda: self.run_async(self.controller.bridge_stop))
        layout.addWidget(start_btn)
        layout.addWidget(stop_btn)
        layout.addStretch()
        return box


class SeedModuleWidget(ModuleWidget):
    """Seed DNA / Mutation engine orchestration."""

    def __init__(self, controller: AppController) -> None:
        self.seed_input = QLineEdit()
        self.mutate_checkbox = QCheckBox("Mutate")
        super().__init__(controller, "Seed Inspector")

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Seed Management")
        layout = QFormLayout(box)
        self.seed_input.setPlaceholderText("Enter seed phrase")
        self.seed_input.setToolTip("Seed phrase to be encoded into 5D geometry")
        layout.addRow("Seed Phrase", self.seed_input)
        self.mutate_checkbox.setToolTip("Generate a mutated variant via MutationEngine")
        layout.addRow("Options", self.mutate_checkbox)
        add_btn = QPushButton("Inscribe Seed Signature")
        add_btn.setToolTip("Encode seed phrase and log activity")
        add_btn.clicked.connect(self._handle_add_seed)
        cluster_btn = QPushButton("Organize Seed Constellation")
        cluster_btn.setToolTip("Run clustering across encoded seeds")
        cluster_btn.clicked.connect(
            lambda: self.run_async(
                self.controller.cluster_seeds,
                on_success=self._on_cluster_complete,
            )
        )
        export_btn = QPushButton("Share Kernel Snapshot…")
        export_btn.setToolTip("Export the Web3 kernel state as JSON")
        export_btn.clicked.connect(self._handle_export_kernel)
        layout.addRow(add_btn)
        layout.addRow(cluster_btn)
        layout.addRow(export_btn)
        if not self.controller.web3_enabled:
            notice = QLabel("Enable Web3 expansion from Settings to activate the inspector.")
            notice.setWordWrap(True)
            layout.addRow(notice)
            for button in (add_btn, cluster_btn, export_btn):
                button.setEnabled(False)
        return box

    def _handle_add_seed(self) -> None:
        phrase = self.seed_input.text()
        mutate = self.mutate_checkbox.isChecked()

        def callback() -> List[float]:
            geometry = self.controller.add_seed_phrase(phrase, mutate=mutate)
            return geometry

        self.run_async(
            callback,
            on_success=lambda geometry: self.log_console.append_message(
                "INFO", f"Seed encoded → norm={sum(map(float, geometry)):.3f}"
            ),
        )

    def _handle_export_kernel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export kernel state", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        destination = Path(path)
        self.run_async(
            self._export_kernel_snapshot,
            destination,
            on_success=lambda result: self.log_console.append_message(
                "INFO", f"Kernel state exported to {result}"
            ),
        )

    def _on_cluster_complete(self, result: object) -> None:
        self.log_console.append_message("INFO", f"Cluster labels: {list(result)}")

    def _export_kernel_snapshot(self, destination: Path) -> Path:
        data = self.controller.kernel_snapshot()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return destination


class CellManagerModuleWidget(ModuleWidget):
    """Supervisor and MetaMemory insights for GabrielCell swarms."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "MetaMemory Core")
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_state)
        self.refresh_timer.start(2000)

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Lifecycle Insights")
        layout = QVBoxLayout(box)
        self.snapshot_tree = QTreeWidget()
        self.snapshot_tree.setHeaderLabels(["Metric", "Value"])
        self.snapshot_tree.setToolTip("Supervisor snapshot values")
        history_btn = QPushButton("Browse MetaMemory Timeline")
        history_btn.setToolTip("Display the stored activity history")
        history_btn.clicked.connect(self._show_history)
        layout.addWidget(self.snapshot_tree)
        layout.addWidget(history_btn)
        return box

    def _refresh_state(self) -> None:
        snapshot = self.controller.supervisor_snapshot()
        self.snapshot_tree.clear()
        for key, value in snapshot.items():
            item = QTreeWidgetItem([key, f"{value:.3f}"])
            self.snapshot_tree.addTopLevelItem(item)
        self.preview.plot_heatmap(self.controller.reverb_activity())

    def _show_history(self) -> None:
        history = self.controller.meta_history()[-10:]
        for entry in history:
            self.log_console.append_message("INFO", f"History → {entry}")


class MetaMemoryModuleWidget(ModuleWidget):
    """Dedicated timeline of MetaMemory snapshots."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Event Playback")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timeline)
        self.timer.start(4000)

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Timeline")
        layout = QVBoxLayout(box)
        self.timeline = QTextEdit()
        self.timeline.setReadOnly(True)
        self.timeline.setToolTip("Recent MetaMemory entries")
        layout.addWidget(self.timeline)
        export_btn = QPushButton("Share Timeline CSV…")
        export_btn.setToolTip("Export MetaMemory history to CSV")
        export_btn.clicked.connect(self._export_history)
        layout.addWidget(export_btn)
        return box

    def _update_timeline(self) -> None:
        history = self.controller.meta_history()[-20:]
        self.timeline.clear()
        for entry in history:
            self.timeline.append(json.dumps(entry, indent=2))
        self.preview.plot_heatmap(self.controller.reverb_activity())

    def _export_history(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export MetaMemory", str(Path.cwd()), "CSV (*.csv)")
        if not path:
            return
        history = self.controller.meta_history()
        with open(path, "w", encoding="utf-8") as handle:
            for entry in history:
                line = ",".join(f"{key}={value}" for key, value in entry.items())
                handle.write(line + "\n")
        self.log_console.append_message("INFO", f"MetaMemory exported to {path}")


class SupervisorModuleWidget(ModuleWidget):
    """Supervisor configuration panel with live updates."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Module Status Console")

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Live Controls")
        layout = QFormLayout(box)
        activity_input = QLineEdit()
        activity_input.setPlaceholderText("activity=value,…")
        activity_input.setToolTip("Comma separated activity updates for the supervisor")
        push_btn = QPushButton("Inject Activity Signal")
        push_btn.setToolTip("Update the supervisor interface with custom values")

        def push_activity() -> None:
            raw = activity_input.text()
            if not raw:
                return
            try:
                activity: Dict[str, float] = {}
                for part in raw.split(","):
                    key, value = part.split("=")
                    activity[key.strip()] = float(value)
                self.controller.supervisor.update(activity)
                self.controller.meta_memory.store(activity)
                self.controller.reverb_ring.log(activity)
                self.log_console.append_message("INFO", f"Injected supervisor activity: {activity}")
            except Exception as exc:  # noqa: BLE001 - user input errors
                self.log_console.append_message("ERROR", f"Invalid activity format: {exc}")
                self.request_notification.emit("Invalid activity", str(exc))

        push_btn.clicked.connect(push_activity)
        layout.addRow("Activity", activity_input)
        layout.addRow(push_btn)
        return box


# ---------------------------------------------------------------------------
# Pipeline orchestrator module
# ---------------------------------------------------------------------------


class PipelineModuleWidget(ModuleWidget):
    """Interactive control surface for the pipeline orchestrator."""

    def __init__(self, controller: AppController) -> None:
        self.proxy_enabled = QCheckBox("Route via Proxy")
        self.proxy_host = QLineEdit()
        self.proxy_port = QSpinBox()
        self.proxy_user = QLineEdit()
        self.proxy_pass = QLineEdit()
        self.result_tree = QTreeWidget()
        self.fixpunkt_output = QTextEdit()
        self.proxy_port.setRange(0, 65535)
        self.proxy_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.result_tree.setHeaderLabels(["Generator", "Stage Count", "Dispatch"])
        self.fixpunkt_output.setReadOnly(True)
        self.fixpunkt_output.setPlaceholderText("Fixpunkt consensus result will appear here")
        super().__init__(controller, "Pipeline Manager")
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_preview)
        self.refresh_timer.start(3500)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Pipeline Controls")
        layout = QVBoxLayout(panel)

        control_group = QGroupBox("Orchestrator Cycle")
        control_layout = QVBoxLayout(control_group)
        run_btn = QPushButton("Launch Resonance Cycle")
        run_btn.setToolTip("Execute the orchestrator pipeline across all generators")
        run_btn.clicked.connect(self._run_pipeline)
        fixpunkt_btn = QPushButton("Resolve Fixpunkt Target")
        fixpunkt_btn.setToolTip("Run the Fixpunkt attractor to obtain a consensus candidate")
        fixpunkt_btn.clicked.connect(self._run_fixpunkt)
        control_layout.addWidget(run_btn)
        control_layout.addWidget(fixpunkt_btn)
        layout.addWidget(control_group)

        layout.addWidget(self.result_tree)

        fixpunkt_group = QGroupBox("Consensus Output")
        fix_layout = QVBoxLayout(fixpunkt_group)
        fix_layout.addWidget(self.fixpunkt_output)
        layout.addWidget(fixpunkt_group)

        proxy_group = QGroupBox("Proxy Routing")
        proxy_form = QFormLayout(proxy_group)
        self.proxy_host.setPlaceholderText("host")
        self.proxy_user.setPlaceholderText("username (optional)")
        self.proxy_pass.setPlaceholderText("password (optional)")
        proxy_form.addRow(self.proxy_enabled)
        proxy_form.addRow("Host", self.proxy_host)
        proxy_form.addRow("Port", self.proxy_port)
        proxy_form.addRow("Username", self.proxy_user)
        proxy_form.addRow("Password", self.proxy_pass)
        apply_btn = QPushButton("Commit Proxy Routing")
        apply_btn.setToolTip("Update orchestrator proxy routing settings")
        apply_btn.clicked.connect(self._apply_proxy)
        proxy_form.addRow(apply_btn)
        layout.addWidget(proxy_group)

        blueprint_btn = QPushButton("Adopt Loaded Blueprint")
        blueprint_btn.setToolTip("Apply the last loaded YAML configuration to the orchestrator")
        blueprint_btn.clicked.connect(self._apply_blueprint)
        layout.addWidget(blueprint_btn)

        layout.addStretch()
        return panel

    def _run_pipeline(self) -> None:
        self.run_async(
            self.controller.run_pipeline_cycle,
            on_success=self._display_pipeline_results,
        )

    def _run_fixpunkt(self) -> None:
        self.run_async(
            self.controller.run_fixpunkt_cycle,
            on_success=self._display_fixpunkt_result,
        )

    def _apply_proxy(self) -> None:
        self.controller.update_proxy_settings(
            enabled=self.proxy_enabled.isChecked(),
            host=self.proxy_host.text() or None,
            port=self.proxy_port.value() or None,
            username=self.proxy_user.text() or None,
            password=self.proxy_pass.text() or None,
        )
        self.log_console.append_message("INFO", "Proxy routing updated for orchestrator")

    def _apply_blueprint(self) -> None:
        config = self.controller._last_config
        if isinstance(config, Mapping):
            self.controller.apply_pipeline_blueprint(config)
            self.log_console.append_message("INFO", "Applied blueprint from configuration editor")
        else:
            self.log_console.append_message("WARNING", "Load a pipeline configuration before applying")

    def _display_pipeline_results(self, results: List[Mapping[str, Any]]) -> None:
        self.result_tree.clear()
        for item in results:
            generator = str(item.get("generator", "unknown"))
            stages = len(item.get("stages", []))
            dispatch = item.get("dispatch", [])
            root = QTreeWidgetItem([generator, str(stages), str(dispatch)])
            self.result_tree.addTopLevelItem(root)
            for index, stage in enumerate(item.get("stages", [])):
                child = QTreeWidgetItem([f"Stage {index+1}", "", str(stage)])
                root.addChild(child)
        self.result_tree.expandAll()
        self.preview.plot_series(
            [len(item.get("stages", [])) for item in results],
            title="Orchestrator Stage Depth",
            ylabel="Stages",
        )

    def _display_fixpunkt_result(self, result: Optional[MutableMapping[str, Any]]) -> None:
        if not result:
            self.fixpunkt_output.setPlainText("No consensus candidate was produced.")
        else:
            self.fixpunkt_output.setPlainText(json.dumps(result, indent=2))

    def _refresh_preview(self) -> None:
        metrics = self.controller.pipeline_stage_lengths()
        if metrics:
            self.preview.plot_series(metrics, title="Recent Stage Depth", ylabel="Stages")


# ---------------------------------------------------------------------------
# Phantomload / traffic resonance module
# ---------------------------------------------------------------------------


class ResonanceLabModuleWidget(ModuleWidget):
    """Command module for the Phantomload traffic resonance lab."""

    def __init__(self, controller: AppController) -> None:
        self.mode_combo = QComboBox()
        self.node_spin = QSpinBox()
        self.mutate_box = QCheckBox("Generate Mutants")
        self.autostart_box = QCheckBox("Auto-start heartbeat")
        self.proxy_mode_combo = QComboBox()
        self.proxy_input = QTextEdit()
        self.status_tree = QTreeWidget()
        super().__init__(controller, "Traffic Pattern Control")
        self.mode_combo.addItems(["resonance", "sweep", "pressure"])
        self.node_spin.setRange(1, 512)
        self.node_spin.setValue(64)
        self.autostart_box.setChecked(True)
        self.proxy_mode_combo.addItems(["round_robin", "random"])
        self.proxy_input.setPlaceholderText("One proxy per line or comma separated")
        self.status_tree.setHeaderLabels(["Metric", "Value"])
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._refresh_status)
        self.status_timer.start(2000)

    def _create_control_panel(self) -> QWidget:
        panel = QGroupBox("Resonance Pulse")
        layout = QVBoxLayout(panel)

        launch_group = QGroupBox("Pulse Deployment")
        launch_form = QFormLayout(launch_group)
        launch_form.addRow("Mode", self.mode_combo)
        launch_form.addRow("Nodes", self.node_spin)
        launch_form.addRow("Mutation", self.mutate_box)
        launch_form.addRow("Autostart", self.autostart_box)
        launch_btn = QPushButton("Deploy Resonance Pulse")
        launch_btn.setToolTip("Spawn phantom nodes and begin the resonance heartbeat")
        launch_btn.clicked.connect(self._launch_pulse)
        halt_btn = QPushButton("Cease Pulse")
        halt_btn.setToolTip("Stop the heartbeat and clear nodes")
        halt_btn.clicked.connect(lambda: self.run_async(self.controller.halt_resonance_pulse))
        launch_form.addRow(launch_btn)
        launch_form.addRow(halt_btn)
        layout.addWidget(launch_group)

        status_group = QGroupBox("Kernel Status")
        status_layout = QVBoxLayout(status_group)
        status_layout.addWidget(self.status_tree)
        layout.addWidget(status_group)

        proxy_group = QGroupBox("Proxy Rotation")
        proxy_layout = QFormLayout(proxy_group)
        proxy_layout.addRow("Mode", self.proxy_mode_combo)
        proxy_layout.addRow("Endpoints", self.proxy_input)
        proxy_btn = QPushButton("Commit Proxy Rotation")
        proxy_btn.setToolTip("Update the proxy list used by phantom nodes")
        proxy_btn.clicked.connect(self._apply_proxy_settings)
        proxy_layout.addRow(proxy_btn)
        layout.addWidget(proxy_group)

        export_btn = QPushButton("Capture Mesh Snapshot…")
        export_btn.setToolTip("Export the current phantom mesh snapshot to JSON")
        export_btn.clicked.connect(self._export_snapshot)
        layout.addWidget(export_btn)

        layout.addStretch()
        return panel

    def _launch_pulse(self) -> None:
        self.run_async(
            lambda: self.controller.launch_resonance_pulse(
                mode=self.mode_combo.currentText(),
                nodes=self.node_spin.value(),
                mutate=self.mutate_box.isChecked(),
                autostart=self.autostart_box.isChecked(),
            ),
            on_success=lambda status: self._update_status_tree(status),
        )

    def _apply_proxy_settings(self) -> None:
        raw = self.proxy_input.toPlainText().replace("\n", ",")
        proxies = [entry.strip() for entry in raw.split(",") if entry.strip()]
        self.controller.phantom_update_proxies(proxies, mode=self.proxy_mode_combo.currentText())
        self.log_console.append_message("INFO", "Updated phantom proxy rotation")

    def _export_snapshot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export traffic mesh",
            str(Path.cwd()),
            "JSON (*.json)",
        )
        if not path:
            return
        self.run_async(self.controller.export_phantom_mesh, Path(path))

    def _refresh_status(self) -> None:
        status = self.controller.phantom_status()
        self._update_status_tree(status)
        snapshot = self.controller.phantom_mesh_snapshot()
        self.preview.plot_network_snapshot(snapshot)

    def _update_status_tree(self, status: Mapping[str, Any]) -> None:
        self.status_tree.clear()
        for key, value in status.items():
            if isinstance(value, (list, tuple)):
                value_repr = ", ".join(map(str, value))
            else:
                value_repr = str(value)
            self.status_tree.addTopLevelItem(QTreeWidgetItem([str(key), value_repr]))

# ---------------------------------------------------------------------------
# Export / Import module
# ---------------------------------------------------------------------------


class ExportImportModuleWidget(ModuleWidget):
    """Unified export/import workflows for mesh, seeds and activity."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Export Tools")

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Data Exchange")
        layout = QVBoxLayout(box)
        mesh_btn = QPushButton("Deliver Mesh Blueprint…")
        mesh_btn.setToolTip("Export mesh data to JSON for Seraphic Swarm")
        mesh_btn.clicked.connect(self._export_mesh)
        seeds_btn = QPushButton("Broadcast Seed Ledger…")
        seeds_btn.setToolTip("Export encoded seeds to CSV")
        seeds_btn.clicked.connect(self._export_seeds)
        if not self.controller.web3_enabled:
            seeds_btn.setEnabled(False)
            seeds_btn.setToolTip(
                "Enable the Web3 expansion pack in Settings to export the seed ledger."
            )
        activity_btn = QPushButton("Transmit Activity Telemetry…")
        activity_btn.setToolTip("Export ReverbRing activity log")
        activity_btn.clicked.connect(self._export_activity)
        import_cfg_btn = QPushButton("Load Strategy Override…")
        import_cfg_btn.setToolTip("Load configuration overrides from YAML")
        import_cfg_btn.clicked.connect(self._import_config)
        layout.addWidget(mesh_btn)
        layout.addWidget(seeds_btn)
        layout.addWidget(activity_btn)
        layout.addWidget(import_cfg_btn)
        layout.addStretch()
        return box

    def _export_mesh(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export mesh", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        self.run_async(self.controller.export_mesh, Path(path))

    def _export_seeds(self) -> None:
        if not self.controller.web3_enabled:
            self.log_console.append_message(
                "WARNING", "Web3 expansion disabled. Activate it in Settings to export seeds."
            )
            self.request_notification.emit(
                "Seed export unavailable",
                "Enable the Web3 expansion pack from Settings before exporting the ledger.",
            )
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export seeds", str(Path.cwd()), "CSV (*.csv)")
        if not path:
            return
        seeds = self.controller.seed_vectors()
        with open(path, "w", encoding="utf-8") as handle:
            for seed in seeds:
                handle.write(",".join(str(value) for value in seed) + "\n")
        self.log_console.append_message("INFO", f"Exported {len(seeds)} seeds to {path}")

    def _export_activity(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export activity", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        data = self.controller.reverb_activity()
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.log_console.append_message("INFO", f"Activity exported to {path}")

    def _import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import YAML", str(Path.cwd()), "YAML (*.yaml *.yml)")
        if not path:
            return
        try:
            config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            if not isinstance(config, MutableMapping):
                raise ValueError("Configuration must be a mapping")
            self.controller._last_config = config
            self.log_console.append_message("INFO", f"Imported configuration from {path}")
        except Exception as exc:  # noqa: BLE001 - YAML parsing errors
            self.log_console.append_message("ERROR", f"Failed to import configuration: {exc}")
            self.request_notification.emit("Config import failed", str(exc))


# ---------------------------------------------------------------------------
# Activity / Logs module
# ---------------------------------------------------------------------------


class ActivityLogsModuleWidget(ModuleWidget):
    """Aggregated logging and notification history."""

    def __init__(self, controller: AppController, emitter: LogSignalEmitter) -> None:
        self.emitter = emitter
        super().__init__(controller, "Alerts & Activity")
        emitter.log_record.connect(self.log_console.append_message)

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Live Activity")
        layout = QVBoxLayout(box)
        refresh_btn = QPushButton("Sync Latest Activity")
        refresh_btn.setToolTip("Pull the latest supervisor snapshot and meta history")
        refresh_btn.clicked.connect(self._refresh)
        layout.addWidget(refresh_btn)
        layout.addStretch()
        return box

    def _refresh(self) -> None:
        snapshot = self.controller.supervisor_snapshot()
        self.log_console.append_message("INFO", f"Supervisor: {snapshot}")
        self.log_console.append_message("INFO", f"MetaMemory length: {len(self.controller.meta_history())}")


# ---------------------------------------------------------------------------
# Realtime heatmap module
# ---------------------------------------------------------------------------


class HeatmapModuleWidget(ModuleWidget):
    """Realtime visualisation of ReverbRing activity."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "Realtime Heatmap")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_heatmap)
        self.timer.start(1500)

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Heatmap Tools")
        layout = QVBoxLayout(box)
        trigger_btn = QPushButton("Stimulate Resonance Pulse")
        trigger_btn.setToolTip("Generate mock activity pulses for demonstration")
        trigger_btn.clicked.connect(self._simulate_activity)
        layout.addWidget(trigger_btn)
        layout.addStretch()
        return box

    def _simulate_activity(self) -> None:
        activity = {
            "seed": random.random() * 2,
            "timestamp": time.time(),
        }
        self.controller.reverb_ring.log(activity)
        self.log_console.append_message("INFO", f"Simulated activity: {activity}")

    def _update_heatmap(self) -> None:
        data = self.controller.reverb_activity()
        self.preview.plot_heatmap(data)


# ---------------------------------------------------------------------------
# Configuration module
# ---------------------------------------------------------------------------


class ConfigModuleWidget(ModuleWidget):
    """Live YAML editor with validation feedback."""

    def __init__(self, controller: AppController) -> None:
        super().__init__(controller, "YAML / JSON Editor")
        self.config_editor: Optional[QTextEdit] = None
        self.config_tree: Optional[QTreeWidget] = None
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._refresh_tree)

    def _create_control_panel(self) -> QWidget:
        box = QGroupBox("Configuration Editor")
        layout = QVBoxLayout(box)
        loader_layout = QHBoxLayout()
        loader_combo = QComboBox()
        loader_combo.addItems(["pipeline", "phosphoros_web3", "phantomload"])
        loader_combo.setToolTip("Choose reference configuration to load")
        load_btn = QPushButton("Pull Template")
        load_btn.setToolTip("Load the selected configuration template")

        def load_config() -> None:
            try:
                config = self.controller.load_config(loader_combo.currentText())
                text = yaml.safe_dump(dict(config), sort_keys=False, allow_unicode=True)
                if self.config_editor:
                    self.config_editor.setText(text)
            except Exception as exc:  # noqa: BLE001 - config load issues
                self.log_console.append_message("ERROR", str(exc))
                self.request_notification.emit("Config load failed", str(exc))

        load_btn.clicked.connect(load_config)
        loader_layout.addWidget(loader_combo)
        loader_layout.addWidget(load_btn)
        layout.addLayout(loader_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.config_editor = QTextEdit()
        self.config_editor.setPlaceholderText("Edit YAML configuration here")
        self.config_editor.textChanged.connect(lambda: self.debounce_timer.start(400))
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabels(["Key", "Value"])
        splitter.addWidget(self.config_editor)
        splitter.addWidget(self.config_tree)
        layout.addWidget(splitter)

        validate_btn = QPushButton("Confirm Configuration")
        validate_btn.setToolTip("Validate YAML syntax and structure")
        validate_btn.clicked.connect(self._refresh_tree)
        layout.addWidget(validate_btn)
        return box

    def _refresh_tree(self) -> None:
        if not self.config_editor or not self.config_tree:
            return
        text = self.config_editor.toPlainText()
        try:
            config = self.controller.validate_yaml(text)
        except Exception as exc:  # noqa: BLE001
            self.config_tree.clear()
            error_item = QTreeWidgetItem(["Error", str(exc)])
            self.config_tree.addTopLevelItem(error_item)
            self.log_console.append_message("ERROR", f"YAML validation failed: {exc}")
            self.request_notification.emit("YAML error", str(exc))
            return
        self.config_tree.clear()
        self._populate_tree(self.config_tree.invisibleRootItem(), config)
        self.log_console.append_message("INFO", "Configuration validated successfully")

    def _populate_tree(self, parent: QTreeWidgetItem, data: Mapping[str, Any]) -> None:
        for key, value in data.items():
            if isinstance(value, Mapping):
                item = QTreeWidgetItem([str(key), ""])
                parent.addChild(item)
                self._populate_tree(item, value)
            elif isinstance(value, list):
                item = QTreeWidgetItem([str(key), f"[{len(value)} items]"])
                parent.addChild(item)
                for index, entry in enumerate(value):
                    child = QTreeWidgetItem([f"[{index}]", json.dumps(entry)])
                    item.addChild(child)
            else:
                item = QTreeWidgetItem([str(key), json.dumps(value)])
                parent.addChild(item)


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------


class SettingsDialog(QDialog):
    """Global application settings (theme, language, API keys)."""

    settings_applied = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(480, 320)
        layout = QVBoxLayout(self)

        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText("Dark")
        theme_layout.addWidget(self.theme_combo)

        lang_group = QGroupBox("Language")
        lang_layout = QVBoxLayout(lang_group)
        self.language_combo = QComboBox()
        self.language_combo.addItems([QLocale.languageToString(QLocale().language()) or "English", "English"])
        lang_layout.addWidget(self.language_combo)

        expansion_group = QGroupBox("Expansion Packs")
        expansion_layout = QVBoxLayout(expansion_group)
        self.web3_checkbox = QCheckBox("Enable Web3 Resonance Pack")
        self.web3_checkbox.setToolTip(
            "Activate the optional Web3 modules (Seed Engine, MetaMemory, Supervisor)."
        )
        expansion_layout.addWidget(self.web3_checkbox)
        self.quantum_checkbox = QCheckBox("Enable Quantum Finance Pack")
        self.quantum_checkbox.setToolTip("Expose swarm trading, hedge controls, and CSP tooling.")
        expansion_layout.addWidget(self.quantum_checkbox)
        self.phantom_checkbox = QCheckBox("Enable Phantomload Pack")
        self.phantom_checkbox.setToolTip("Enable phantomload resonance lab tooling.")
        expansion_layout.addWidget(self.phantom_checkbox)

        link_group = QGroupBox("ShadowGraph Link")
        link_form = QFormLayout(link_group)
        self.shadowgraph_endpoint = QLineEdit()
        self.shadowgraph_endpoint.setPlaceholderText(
            "https://shadowgraph.local/api/hooks/ainsoft"
        )
        self.shadowgraph_endpoint.setToolTip(
            "Public AinSOFT endpoint ShadowGraph clients can query"
        )
        self.shadowgraph_token = QLineEdit()
        self.shadowgraph_token.setPlaceholderText("Optional shared secret for inbound sync")
        self.shadowgraph_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.shadowgraph_token.setToolTip(
            "Shared token that ShadowGraph presents when connecting to AinSOFT"
        )
        link_form.addRow("AinSOFT Endpoint", self.shadowgraph_endpoint)
        link_form.addRow("Link Token", self.shadowgraph_token)

        export_group = QGroupBox("Config Export")
        export_layout = QHBoxLayout(export_group)
        export_path_edit = QLineEdit(str(Path.cwd() / "configs"))
        export_path_edit.setToolTip("Directory for exported configuration files")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(
            lambda: self._select_directory(export_path_edit)
        )
        export_layout.addWidget(export_path_edit)
        export_layout.addWidget(browse_btn)

        button_bar = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(lambda: self._apply_settings(export_path_edit.text()))
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_bar.addStretch()
        button_bar.addWidget(apply_btn)
        button_bar.addWidget(close_btn)

        layout.addWidget(theme_group)
        layout.addWidget(lang_group)
        layout.addWidget(expansion_group)
        layout.addWidget(link_group)
        layout.addWidget(export_group)
        layout.addLayout(button_bar)

    def _select_directory(self, edit: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select directory", edit.text())
        if directory:
            edit.setText(directory)

    def _apply_settings(self, export_path: str) -> None:
        settings = {
            "theme": self.theme_combo.currentText().lower(),
            "language": self.language_combo.currentText(),
            "web3_enabled": self.web3_checkbox.isChecked(),
            "quantum_enabled": self.quantum_checkbox.isChecked(),
            "phantom_enabled": self.phantom_checkbox.isChecked(),
            "shadowgraph_endpoint": self.shadowgraph_endpoint.text(),
            "shadowgraph_token": self.shadowgraph_token.text(),
            "export_path": export_path,
        }
        self.settings_applied.emit(settings)
        self.close()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


@dataclass
class ModuleEntry:
    name: str
    widget: ModuleWidget
    icon: QIcon
    zone: str
    subzone: Optional[str] = None


@dataclass
class ModuleSpec:
    factory: Callable[[], ModuleWidget]
    icon_name: str
    zone: str
    subzone: Optional[str] = None


class MainWindow(QMainWindow):
    """Main application window with navigation, search and notifications."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AinSOFT Control Center")
        self.resize(1400, 900)
        self.controller = AppController()
        self.log_emitter = LogSignalEmitter()
        self.translator = QTranslator()
        self._modules: List[ModuleEntry] = []
        self.zone_buttons: Dict[int, QToolButton] = {}
        self._active_module_index: Optional[int] = None
        self._zone_structure: "OrderedDict[str, List[str]]" = OrderedDict(
            [
                ("Dashboard", []),
                ("Exploration", []),
                ("Orchestration", []),
                ("Resonance Lab", []),
                (
                    "Expansion Packs",
                    [
                        "Quantum Finance",
                        "Web3 / Blockchain Forensics",
                        "Phantomload",
                    ],
                ),
                ("Settings", []),
                ("Help", []),
            ]
        )
        self._zone_mapping: Dict[str, Tuple[str, Optional[str]]] = {
            "Operations Dashboard": ("Dashboard", None),
            "Target Acquisition Console": ("Dashboard", None),
            "Alerts & Activity": ("Dashboard", None),
            "Module Status Console": ("Dashboard", None),
            "Data Import": ("Exploration", None),
            "Seed Inspector": ("Exploration", None),
            "Cluster Map": ("Exploration", None),
            "Realtime Heatmap": ("Exploration", None),
            "Export Tools": ("Exploration", None),
            "Pipeline Manager": ("Orchestration", None),
            "Mutation Engine": ("Orchestration", None),
            "MetaMemory Core": ("Orchestration", None),
            "Scorpio Bridge / Sync": ("Orchestration", None),
            "3D Mesh Viewer": ("Resonance Lab", None),
            "Spectral Scanner": ("Resonance Lab", None),
            "Event Playback": ("Resonance Lab", None),
            "Swarm Trading": ("Expansion Packs", "Quantum Finance"),
            "Hedge Controls": ("Expansion Packs", "Quantum Finance"),
            "CSP Engine": ("Expansion Packs", "Quantum Finance"),
            "DeFi Connector": ("Expansion Packs", "Quantum Finance"),
            "Strategies / Audit": ("Expansion Packs", "Quantum Finance"),
            "Node Scanner": ("Expansion Packs", "Web3 / Blockchain Forensics"),
            "Sybil Detection": ("Expansion Packs", "Web3 / Blockchain Forensics"),
            "GhostRPC": ("Expansion Packs", "Web3 / Blockchain Forensics"),
            "Identity Clustering": ("Expansion Packs", "Web3 / Blockchain Forensics"),
            "Mycelium Visualization": ("Expansion Packs", "Web3 / Blockchain Forensics"),
            "Traffic Pattern Control": ("Expansion Packs", "Phantomload"),
            "Attack Sim": ("Expansion Packs", "Phantomload"),
            "Stealth Tools": ("Expansion Packs", "Phantomload"),
            "Export / Protocol": ("Expansion Packs", "Phantomload"),
            "YAML / JSON Editor": ("Settings", None),
            "Profiles": ("Settings", None),
            "Licensing & API": ("Settings", None),
            "Integration Hub": ("Settings", None),
            "Manual": ("Help", None),
            "Onboarding": ("Help", None),
            "FAQ & Support": ("Help", None),
        }
        self.zone_group_widgets: Dict[Tuple[str, Optional[str]], QGroupBox] = {}
        self.energy_bar = QProgressBar()
        self.connection_bar = QProgressBar()
        self.entropy_label = QLabel("Entropy Level: --")
        self.latency_label = QLabel("Last Pulse: --")
        self.active_colls_label = QLabel("Active Colls: --")
        self._build_ui()
        self._apply_scifi_theme()
        self._install_logging()
        self._setup_timers()
        QApplication.instance().aboutToQuit.connect(self.controller.shutdown)  # type: ignore[arg-type]

    # UI -----------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(24, 24, 24, 24)
        central_layout.setSpacing(20)
        self.setCentralWidget(central)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(24)

        self.zone_group_layouts: Dict[Tuple[str, Optional[str]], QVBoxLayout] = {}
        self.zone_group_widgets = {}
        self.zone_section_groups: Dict[str, QGroupBox] = {}
        self.zone_sidebar = self._create_zone_sidebar()
        body_layout.addWidget(self.zone_sidebar)

        self.center_column = self._create_central_column()
        body_layout.addWidget(self.center_column, 1)

        self.status_column = self._create_status_panel()
        body_layout.addWidget(self.status_column)

        central_layout.addLayout(body_layout, 1)
        central_layout.addWidget(self._create_control_deck())

        self._create_toolbar()
        self._create_statusbar()
        self._register_modules()

    def _create_zone_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("ZoneSidebar")
        sidebar.setMaximumWidth(280)
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(18)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("CONTROL ZONES")
        title.setObjectName("SidebarTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        for zone_name, subzones in self._zone_structure.items():
            group = QGroupBox(zone_name)
            group.setObjectName("ZoneGroup")
            group_layout = QVBoxLayout(group)
            group_layout.setSpacing(12)
            self.zone_section_groups[zone_name] = group
            if subzones:
                for sub in subzones:
                    sub_group = QGroupBox(sub)
                    sub_group.setObjectName("ZoneSubGroup")
                    sub_layout = QVBoxLayout(sub_group)
                    sub_layout.setSpacing(8)
                    self.zone_group_layouts[(zone_name, sub)] = sub_layout
                    self.zone_group_widgets[(zone_name, sub)] = sub_group
                    group_layout.addWidget(sub_group)
            else:
                self.zone_group_layouts[(zone_name, None)] = group_layout
                self.zone_group_widgets[(zone_name, None)] = group
            layout.addWidget(group)

        layout.addStretch()
        return sidebar

    def _create_central_column(self) -> QWidget:
        column = QWidget()
        column_layout = QVBoxLayout(column)
        column_layout.setSpacing(16)
        column_layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("AinSOFT Operations Center")
        header.setObjectName("CommandDeckTitle")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        column_layout.addWidget(header)

        self.module_title_label = QLabel("Select a module to begin")
        self.module_title_label.setObjectName("ModuleTitleLabel")
        column_layout.addWidget(self.module_title_label)

        self.visualizer_tabs = QTabWidget()
        self.visualizer_tabs.setObjectName("VisualizerTabs")
        mesh_tab = QWidget()
        mesh_layout = QVBoxLayout(mesh_tab)
        mesh_layout.setSpacing(8)
        mesh_placeholder = QLabel("Mesh map placeholder – integrate Unity/Unreal feed here")
        mesh_placeholder.setWordWrap(True)
        mesh_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mesh_layout.addWidget(mesh_placeholder, 1)
        self.visualizer_tabs.addTab(mesh_tab, "Mesh Map")

        if MPL_AVAILABLE:
            heatmap_tab = QWidget()
            heatmap_layout = QVBoxLayout(heatmap_tab)
            heatmap_layout.setSpacing(8)
            figure = Figure(figsize=(4, 3))
            canvas = FigureCanvasQTAgg(figure)
            ax = figure.add_subplot(111)
            ax.set_facecolor("#04121a")
            ax.set_title("Signal Density")
            heatmap_layout.addWidget(canvas)
            self.visualizer_tabs.addTab(heatmap_tab, "Signal Density")

        column_layout.addWidget(self.visualizer_tabs, 2)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ModuleStack")
        column_layout.addWidget(self.stack, 3)

        return column

    def _create_status_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("StatusPanel")
        panel.setMaximumWidth(260)
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        readout = QGroupBox("System Readout")
        readout_layout = QVBoxLayout(readout)
        readout_layout.setSpacing(10)
        self.energy_bar.setRange(0, 100)
        self.energy_bar.setValue(58)
        self.energy_bar.setFormat("Energy Reserve: %p%")
        readout_layout.addWidget(self.energy_bar)

        self.connection_bar.setRange(0, 100)
        self.connection_bar.setValue(85)
        self.connection_bar.setFormat("Bridge Uplink: %p%")
        readout_layout.addWidget(self.connection_bar)

        readout_layout.addWidget(self.entropy_label)
        readout_layout.addWidget(self.latency_label)
        readout_layout.addWidget(self.active_colls_label)
        layout.addWidget(readout)

        diagnostics = QGroupBox("Telemetry")
        diag_layout = QVBoxLayout(diagnostics)
        diag_layout.setSpacing(10)
        self.bridge_status_label = QLabel("Bridge Status: Initialising…")
        self.seed_status_label = QLabel("Seed Cache: --")
        diag_layout.addWidget(self.bridge_status_label)
        diag_layout.addWidget(self.seed_status_label)
        layout.addWidget(diagnostics)

        layout.addStretch()
        return panel

    def _create_control_deck(self) -> QWidget:
        deck = QWidget()
        deck.setObjectName("ControlDeck")
        layout = QHBoxLayout(deck)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(18)

        self.bridge_control_btn = QPushButton("Initiate Bridge Link")
        self.bridge_control_btn.setToolTip("Start the Scorpio Bridge heartbeat to establish the uplink")
        self.bridge_control_btn.clicked.connect(
            lambda: self._enqueue_operation("Bridge uplink", self.controller.bridge_start)
        )

        self.mesh_control_btn = QPushButton("Stabilize Mesh Field")
        self.mesh_control_btn.setToolTip("Run mesh solve to stabilise current field resonance")
        self.mesh_control_btn.clicked.connect(
            lambda: self._enqueue_operation("Mesh stabilisation", self.controller.solve_mesh)
        )

        self.sensor_control_btn = QPushButton("Trigger Sensor Sweep")
        self.sensor_control_btn.setToolTip("Request a fresh sensor sweep via the pointcloud inspector")
        self.sensor_control_btn.clicked.connect(
            lambda: self._enqueue_operation("Sensor sweep", self.controller.refresh_pointcloud)
        )

        for button in (self.bridge_control_btn, self.mesh_control_btn, self.sensor_control_btn):
            button.setObjectName("DeckButton")
            button.setMinimumHeight(72)
            layout.addWidget(button)

        return deck

    def _enqueue_operation(self, description: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        worker = Worker(func, *args, **kwargs)

        def on_start() -> None:
            self.statusBar().showMessage(f"{description} in progress…")

        def on_finish(_: object) -> None:
            self.statusBar().showMessage(f"{description} complete")
            self._update_status_panel()

        def on_error(message: str) -> None:
            self._show_notification(f"{description} failed", message)

        worker.signals.started.connect(on_start)
        worker.signals.finished.connect(on_finish)
        worker.signals.error.connect(on_error)
        self.controller.thread_pool.start(worker)

    def _apply_scifi_theme(self) -> None:
        palette = self.palette()
        background = QColor("#101622")
        surface = QColor("#161d2b")
        accent = QColor("#2dd4bf")
        text = QColor("#e5e9f0")
        palette.setColor(QPalette.ColorRole.Window, background)
        palette.setColor(QPalette.ColorRole.Base, QColor("#131b2b"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1b2333"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#1c2a3b"))
        palette.setColor(QPalette.ColorRole.Text, text)
        palette.setColor(QPalette.ColorRole.ButtonText, text)
        palette.setColor(QPalette.ColorRole.Highlight, accent)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#071422"))
        self.setPalette(palette)

        font = QFont("IBM Plex Sans", 10)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self.setFont(font)

        style = """
            QMainWindow, QWidget {
                background-color: #101622;
                color: #e5e9f0;
                font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
            }
            QLabel#CommandDeckTitle {
                font-size: 24px;
                font-weight: 600;
                letter-spacing: 2px;
                color: #2dd4bf;
            }
            QLabel#ModuleTitleLabel {
                font-size: 14px;
                letter-spacing: 1px;
                color: #9caac6;
            }
            QWidget#ZoneSidebar {
                background-color: #161d2b;
                border: 1px solid rgba(45, 212, 191, 0.25);
                border-radius: 12px;
                padding: 12px;
            }
            QLabel#SidebarTitle {
                font-size: 12px;
                letter-spacing: 2px;
                text-transform: uppercase;
                color: #7dd3fc;
            }
            QGroupBox, QGroupBox#ZoneSubGroup {
                border: 1px solid rgba(148, 163, 184, 0.35);
                border-radius: 10px;
                margin-top: 12px;
                padding: 10px;
                background-color: #121a28;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                font-size: 11px;
                color: #93c5fd;
            }
            QToolButton {
                background-color: #1b2435;
                border: 1px solid rgba(148, 163, 184, 0.3);
                border-radius: 10px;
                padding: 8px 12px;
                color: #e5e9f0;
                text-align: left;
            }
            QToolButton:hover {
                background-color: #233049;
                border-color: rgba(45, 212, 191, 0.45);
            }
            QToolButton:checked {
                background-color: rgba(45, 212, 191, 0.18);
                border-color: #2dd4bf;
            }
            QPushButton#DeckButton {
                background-color: #1c2a3b;
                border: 1px solid rgba(45, 212, 191, 0.5);
                border-radius: 14px;
                color: #2dd4bf;
                font-size: 15px;
                font-weight: 600;
                padding: 10px 18px;
            }
            QPushButton#DeckButton:hover {
                background-color: #2dd4bf;
                color: #071422;
            }
            QPushButton {
                border-radius: 8px;
                background-color: #1b2537;
                border: 1px solid rgba(148, 163, 184, 0.3);
                padding: 7px 12px;
            }
            QPushButton:hover {
                border-color: #2dd4bf;
            }
            QProgressBar {
                border: 1px solid rgba(148, 163, 184, 0.3);
                border-radius: 8px;
                background: #141c2a;
                color: #e5e9f0;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(45, 212, 191, 0.4), stop:1 rgba(125, 211, 252, 0.8));
                border-radius: 8px;
            }
            QStatusBar {
                background: #161d2b;
                border-top: 1px solid rgba(148, 163, 184, 0.3);
            }
            QTabWidget::pane {
                border: 1px solid rgba(148, 163, 184, 0.3);
                border-radius: 10px;
                background: #121a28;
            }
            QTabBar::tab {
                padding: 6px 16px;
                margin: 2px;
                background: #1b2537;
                border: 1px solid transparent;
                border-radius: 9px;
            }
            QTabBar::tab:selected {
                background: rgba(45, 212, 191, 0.22);
                border-color: rgba(45, 212, 191, 0.6);
            }
        """
        self.setStyleSheet(style)

    def _set_active_module(self, index: int) -> None:
        if index < 0 or index >= len(self._modules):
            return
        self._active_module_index = index
        self.stack.setCurrentIndex(index)
        module = self._modules[index]
        self.module_title_label.setText(f"ACTIVE MODULE · {module.name.upper()}")
        for idx, button in self.zone_buttons.items():
            button.setChecked(idx == index)
        self.statusBar().showMessage(f"Viewing {module.name}")

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Search modules or actions…")
        search_edit.setClearButtonEnabled(True)
        search_edit.textChanged.connect(self._handle_search)
        toolbar.addWidget(search_edit)

        toolbar.addSeparator()

        settings_action = QAction(QIcon.fromTheme("preferences-system"), "Settings", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        theme_action = QAction(QIcon.fromTheme("weather-clear-night"), "Toggle Theme", self)
        theme_action.triggered.connect(self._toggle_theme)
        toolbar.addAction(theme_action)

        help_action = QAction(QIcon.fromTheme("help-contents"), "Help", self)
        help_action.triggered.connect(self._show_help)
        toolbar.addAction(help_action)

    def _create_statusbar(self) -> None:
        status = QStatusBar()
        status.setObjectName("CommandStatusBar")
        self.setStatusBar(status)
        icon_label = QLabel("🛰️")
        icon_label.setStyleSheet("font-size: 18px; margin-right: 8px;")
        status.addWidget(icon_label)
        self.status_message_label = QLabel("🛸 Bridge: Standby")
        status.addWidget(self.status_message_label)
        self.system_status_label = QLabel("SYSTEM STATUS: INITIALISING")
        self.system_status_label.setStyleSheet("letter-spacing: 2px; font-size: 12px;")
        status.addPermanentWidget(self.system_status_label)

    def _clear_zone_navigation(self) -> None:
        for layout in self.zone_group_layouts.values():
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self.zone_buttons.clear()

    def _update_zone_visibility(self) -> None:
        for key, widget in self.zone_group_widgets.items():
            layout = self.zone_group_layouts.get(key)
            if layout is None:
                continue
            has_buttons = any(layout.itemAt(i).widget() is not None for i in range(layout.count()))
            widget.setVisible(has_buttons)

        for zone_name, group in self.zone_section_groups.items():
            subzones = self._zone_structure.get(zone_name, [])
            if subzones:
                visible = any(
                    self.zone_group_widgets.get((zone_name, sub))
                    and self.zone_group_widgets[(zone_name, sub)].isVisible()
                    for sub in subzones
                )
            else:
                widget = self.zone_group_widgets.get((zone_name, None))
                visible = widget.isVisible() if widget else False
            group.setVisible(visible)

    def _register_modules(self) -> None:
        specs: List[ModuleSpec] = [
            ModuleSpec(lambda: DashboardModuleWidget(self.controller), "view-dashboard", "Dashboard"),
            ModuleSpec(lambda: TargetAcquisitionModuleWidget(self.controller), "network-transmit", "Dashboard"),
            ModuleSpec(
                lambda: ActivityLogsModuleWidget(self.controller, self.log_emitter),
                "dialog-information",
                "Dashboard",
            ),
            ModuleSpec(lambda: SupervisorModuleWidget(self.controller), "system-monitor", "Dashboard"),
            ModuleSpec(lambda: DataImportModuleWidget(self.controller), "document-open", "Exploration"),
            ModuleSpec(lambda: SeedModuleWidget(self.controller), "applications-science", "Exploration"),
            ModuleSpec(lambda: PointCloudModuleWidget(self.controller), "view-grid", "Exploration"),
            ModuleSpec(lambda: HeatmapModuleWidget(self.controller), "view-statistics", "Exploration"),
            ModuleSpec(lambda: ExportImportModuleWidget(self.controller), "document-save", "Exploration"),
            ModuleSpec(lambda: PipelineModuleWidget(self.controller), "system-run", "Orchestration"),
            ModuleSpec(lambda: MutationEngineModuleWidget(self.controller), "applications-science", "Orchestration"),
            ModuleSpec(lambda: CellManagerModuleWidget(self.controller), "user-group", "Orchestration"),
            ModuleSpec(lambda: BridgeModuleWidget(self.controller), "media-playback-start", "Orchestration"),
            ModuleSpec(lambda: MeshLayerModuleWidget(self.controller), "network-wireless", "Resonance Lab"),
            ModuleSpec(lambda: SpectralScannerModuleWidget(self.controller), "media-record", "Resonance Lab"),
            ModuleSpec(lambda: MetaMemoryModuleWidget(self.controller), "view-calendar", "Resonance Lab"),
            ModuleSpec(lambda: ConfigModuleWidget(self.controller), "preferences-system", "Settings"),
            ModuleSpec(lambda: ProfilesModuleWidget(self.controller), "user-identity", "Settings"),
            ModuleSpec(lambda: LicensingModuleWidget(self.controller), "emblem-readonly", "Settings"),
            ModuleSpec(lambda: IntegrationModuleWidget(self.controller), "network-server", "Settings"),
            ModuleSpec(lambda: ManualModuleWidget(self.controller), "help-contents", "Help"),
            ModuleSpec(lambda: OnboardingModuleWidget(self.controller), "user-info", "Help"),
            ModuleSpec(lambda: FaqSupportModuleWidget(self.controller), "dialog-question", "Help"),
        ]

        quantum_specs = [
            ModuleSpec(lambda: SwarmTradingModuleWidget(self.controller), "finance", "Expansion Packs", "Quantum Finance"),
            ModuleSpec(lambda: HedgeControlsModuleWidget(self.controller), "view-statistics", "Expansion Packs", "Quantum Finance"),
            ModuleSpec(lambda: CspEngineModuleWidget(self.controller), "applications-engineering", "Expansion Packs", "Quantum Finance"),
            ModuleSpec(lambda: DefiConnectorModuleWidget(self.controller), "network-wireless", "Expansion Packs", "Quantum Finance"),
            ModuleSpec(lambda: StrategyAuditModuleWidget(self.controller), "system-search", "Expansion Packs", "Quantum Finance"),
        ]

        web3_specs = [
            ModuleSpec(lambda: NodeScannerModuleWidget(self.controller), "system-search", "Expansion Packs", "Web3 / Blockchain Forensics"),
            ModuleSpec(lambda: SybilDetectionModuleWidget(self.controller), "security-high", "Expansion Packs", "Web3 / Blockchain Forensics"),
            ModuleSpec(lambda: GhostRpcModuleWidget(self.controller), "network-connect", "Expansion Packs", "Web3 / Blockchain Forensics"),
            ModuleSpec(lambda: IdentityClusteringModuleWidget(self.controller), "view-process-all", "Expansion Packs", "Web3 / Blockchain Forensics"),
            ModuleSpec(lambda: MyceliumVisualizationModuleWidget(self.controller), "view-preview", "Expansion Packs", "Web3 / Blockchain Forensics"),
        ]

        phantom_specs = [
            ModuleSpec(lambda: ResonanceLabModuleWidget(self.controller), "network-server", "Expansion Packs", "Phantomload"),
            ModuleSpec(lambda: AttackSimulationModuleWidget(self.controller), "media-playback-start", "Expansion Packs", "Phantomload"),
            ModuleSpec(lambda: StealthToolsModuleWidget(self.controller), "tools-check-spelling", "Expansion Packs", "Phantomload"),
            ModuleSpec(lambda: PhantomExportModuleWidget(self.controller), "document-save", "Expansion Packs", "Phantomload"),
        ]

        if self.controller.quantum_enabled:
            specs.extend(quantum_specs)
        if self.controller.web3_enabled:
            specs.extend(web3_specs)
        if self.controller.phantom_enabled:
            specs.extend(phantom_specs)

        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self._clear_zone_navigation()
        self._modules.clear()
        self._active_module_index = None

        for spec in specs:
            module = spec.factory()
            icon = QIcon.fromTheme(spec.icon_name)
            entry = ModuleEntry(module.title, module, icon, spec.zone, spec.subzone)
            self._modules.append(entry)
            self.stack.addWidget(module)
            module.request_notification.connect(self._show_notification)

        for index, entry in enumerate(self._modules):
            zone_info = self._zone_mapping.get(entry.name, (entry.zone, entry.subzone))
            zone_layout = self.zone_group_layouts.get(zone_info)
            if zone_layout is None:
                continue
            button = QToolButton()
            button.setIcon(entry.icon)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIconSize(QSize(28, 28))
            button.setText(entry.name)
            button.setToolTip(f"Activate {entry.name} controls")
            button.clicked.connect(lambda checked=False, idx=index: self._set_active_module(idx))
            zone_layout.addWidget(button)
            self.zone_buttons[index] = button

        if self._modules:
            self._set_active_module(0)
        self._update_zone_visibility()
        self._update_status_panel()

    # Logging ------------------------------------------------------------
    def _install_logging(self) -> None:
        handler = QtLogHandler(self.log_emitter)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(handler)

    # Timers -------------------------------------------------------------
    def _setup_timers(self) -> None:
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_statusbar)
        self.status_timer.start(2500)
        QTimer.singleShot(0, self._update_statusbar)

    # Slots --------------------------------------------------------------
    def _handle_search(self, text: str) -> None:
        text_lower = text.lower().strip()
        if not text_lower:
            self.statusBar().showMessage("Ready")
            return

        first_match: Optional[Tuple[int, QWidget]] = None
        for index, entry in enumerate(self._modules):
            module = entry.widget
            if text_lower in entry.name.lower() and first_match is None:
                first_match = (index, module)
            if first_match is None:
                for child in module.findChildren((QPushButton, QLineEdit, QComboBox)):
                    strings: List[str] = []
                    if isinstance(child, QPushButton):
                        strings = [child.text(), child.toolTip()]
                    elif isinstance(child, QLineEdit):
                        strings = [child.placeholderText(), child.toolTip()]
                    elif isinstance(child, QComboBox):
                        strings = [child.currentText(), child.toolTip()]
                    if any(s and text_lower in s.lower() for s in strings):
                        first_match = (index, child)
                        break
            if first_match is not None:
                break

        if first_match:
            index, widget = first_match
            self._set_active_module(index)

            def focus_target() -> None:
                widget.setFocus()

            QTimer.singleShot(150, focus_target)
            hint = getattr(widget, "toolTip", lambda: "")() or getattr(
                widget, "placeholderText", lambda: ""
            )()
            if hint:
                self.statusBar().showMessage(f"Matched: {hint}")
        else:
            self.statusBar().showMessage("No match found")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.web3_checkbox.setChecked(self.controller.web3_enabled)
        dialog.quantum_checkbox.setChecked(self.controller.quantum_enabled)
        dialog.phantom_checkbox.setChecked(self.controller.phantom_enabled)
        dialog.settings_applied.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self, settings: Dict[str, Any]) -> None:
        theme = settings.get("theme", "light")
        if theme == "dark":
            self._apply_scifi_theme()
        else:
            self.setStyleSheet(
                """
                QWidget { background-color: #f5f6fa; color: #1f2933; font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; }
                QGroupBox { border: 1px solid #ced4da; border-radius: 8px; margin-top: 12px; background: #ffffff; }
                QGroupBox::title { subcontrol-origin: margin; padding: 0 8px; color: #495057; }
                QPushButton { background-color: #dee2e6; border: 1px solid #adb5bd; border-radius: 6px; padding: 6px 12px; }
                QPushButton:hover { background-color: #ced4da; }
                QLineEdit, QTextEdit, QPlainTextEdit { background-color: #ffffff; border: 1px solid #adb5bd; border-radius: 6px; }
                QToolButton { background-color: #ffffff; border: 1px solid #adb5bd; border-radius: 6px; padding: 6px 10px; }
                QStatusBar { background: #e9ecef; color: #495057; }
            """
            )

        previous_web3_state = self.controller.web3_enabled
        desired_web3_state = bool(settings.get("web3_enabled", False))
        self.controller.set_web3_enabled(desired_web3_state)
        previous_quantum_state = self.controller.quantum_enabled
        desired_quantum_state = bool(settings.get("quantum_enabled", False))
        self.controller.set_quantum_enabled(desired_quantum_state)
        previous_phantom_state = self.controller.phantom_enabled
        desired_phantom_state = bool(settings.get("phantom_enabled", self.controller.phantom_enabled))
        self.controller.set_phantom_enabled(desired_phantom_state)
        if (
            previous_web3_state != self.controller.web3_enabled
            or previous_quantum_state != self.controller.quantum_enabled
            or previous_phantom_state != self.controller.phantom_enabled
        ):
            self._register_modules()
        else:
            self._update_zone_visibility()
            self._update_status_panel()

        # TODO: integrate QTranslator resources for i18n once available.
        self.statusBar().showMessage("Settings applied")

    def _toggle_theme(self) -> None:
        if self.styleSheet():
            self.setStyleSheet("")
        else:
            self.setStyleSheet(
                """
                QWidget { background-color: #121212; color: #f8f9fa; }
                QPushButton { background-color: #1f1f1f; border: 1px solid #343a40; padding: 6px 12px; }
                QLineEdit, QTextEdit, QPlainTextEdit { background-color: #1f1f1f; border: 1px solid #343a40; }
                QGroupBox { border: 1px solid #343a40; margin-top: 12px; }
                """
            )

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "AinSOFT",
            """Use the navigation sidebar to switch between AinSOFT subsystems.\n
            Each module panel exposes controls for mesh orchestration, optional
            Web3 seed pipelines and telemetry. Tooltips provide concise
            descriptions for every control.""",
        )

    def _show_notification(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def _update_status_panel(self) -> None:
        seeds, clusters = self.controller.seed_counts()
        phantom_status = self.controller.phantom_status()
        phantom_nodes = int(phantom_status.get("nodes", 0))
        phantom_events = int(phantom_status.get("events", 0))
        energy = min(100, max(35, 48 + seeds * 4 + random.randint(-6, 6)))
        base_connection = 88 if self.controller._bridge_running else 42
        connection = min(100, max(25, base_connection + random.randint(-5, 5)))
        entropy = min(1.0, 0.28 + clusters * 0.03 + random.random() * 0.05)
        self.energy_bar.setValue(energy)
        self.connection_bar.setValue(connection)
        self.entropy_label.setText(f"Entropy Level: {entropy:.2f}")
        self.latency_label.setText(
            f"Bridge Pulse: {self.controller.bridge.tick_interval:.3f}s | Traffic Beat: {self.controller.traffic_bridge.tick_interval:.3f}s"
        )
        self.active_colls_label.setText(f"Traffic Nodes: {phantom_nodes} (events {phantom_events})")
        bridge_text = "Bridge Status: Connected" if self.controller._bridge_running else "Bridge Status: Standby"
        self.bridge_status_label.setText(bridge_text)
        if self.controller.web3_enabled:
            self.seed_status_label.setText(f"Seed Cache: {seeds} phrases")
        else:
            self.seed_status_label.setText("Seed Cache: Expansion disabled")

    def _update_statusbar(self) -> None:
        seeds, _ = self.controller.seed_counts()
        bridge = "🛸 Bridge: Connected" if self.controller._bridge_running else "🛸 Bridge: Standby"
        if self.controller.web3_enabled:
            self.status_message_label.setText(f"{bridge}   •   Seeds Online: {seeds}")
        else:
            self.status_message_label.setText(f"{bridge}   •   Web3 expansion offline")
        self.system_status_label.setText("SYSTEM STATUS: ONLINE")
        self._update_status_panel()


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Launch the AinSOFT Control Center."""

    app = QApplication(sys.argv)
    app.setOrganizationName("AinSOFT")
    app.setApplicationName("AinSOFT Control Center")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - manual launch
    run()


# ---------------------------------------------------------------------------
# Install & Run Instructions
# ---------------------------------------------------------------------------
# ```bash
# pip install -e .[gui]  # Ensure PyQt6 and matplotlib are available
# python -m ainsoft.interfaces.gui
# ```
# The GUI uses optional matplotlib previews. Install `matplotlib` to enable the
# charts, otherwise placeholder messaging is shown. Integrate Unity/Unreal mesh
# visualisations by replacing :class:`PreviewCanvas` with engine-specific
# components (see TODO markers within the module).
