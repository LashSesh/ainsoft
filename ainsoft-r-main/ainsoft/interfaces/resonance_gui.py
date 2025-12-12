"""AinSOFT Resonance Pentesting Console (PyQt6 GUI).

This module delivers a streamlined command deck focused exclusively on the
resonance, load orchestration, and proxy tooling that differentiate AinSOFT as
an offensive traffic laboratory.  Operators can acquire targets, compose load
patterns, stage proxy relays, and observe live telemetry from a single modern
PyQt6 window.  The design removes the broader analytics and expansion packs
from the primary control center so that red-team engagements stay focused and
responsive.
"""

from __future__ import annotations

import json
import logging
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette, QTextCharFormat, QTextCursor, QTextOption
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QToolBar,
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


# Ensure the package root is importable when executed as a script.
if __package__ in {None, ""}:  # pragma: no cover - guard for direct execution
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


LOGGER = logging.getLogger("ainsoft.resonance_gui")


def apply_resonance_palette(app: QApplication) -> None:
    """Apply a dark neon palette aligned with the resonance lab aesthetic."""

    palette = QPalette()
    base_color = QColor("#0f0f12")
    accent = QColor("#15f4d0")
    text = QColor("#f5f5f7")
    disabled = QColor("#6b6b6b")

    palette.setColor(QPalette.ColorRole.Window, base_color)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, QColor("#1a1a21"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#121218"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1f1f2a"))
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, QColor("#1c1c24"))
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, accent)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0b0b0f"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, disabled)
    palette.setColor(QPalette.ColorRole.Link, accent)

    app.setPalette(palette)
    app.setStyleSheet(
        """
        QWidget {
            background-color: #0f0f12;
            color: #f5f5f7;
            font-family: 'Orbitron', 'Eurostile', 'Segoe UI', sans-serif;
        }
        QGroupBox {
            border: 1px solid #1f2a30;
            border-radius: 6px;
            margin-top: 18px;
            padding: 12px;
            font-weight: 600;
            letter-spacing: 1px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px 0 6px;
        }
        QPushButton {
            border: 1px solid #15f4d0;
            border-radius: 6px;
            padding: 8px 12px;
            background-color: rgba(21, 244, 208, 0.12);
            color: #f5f5f7;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        QPushButton:hover {
            background-color: rgba(21, 244, 208, 0.24);
        }
        QPushButton:pressed {
            background-color: rgba(21, 244, 208, 0.36);
        }
        QLineEdit, QComboBox, QTextEdit {
            border: 1px solid #222634;
            border-radius: 4px;
            padding: 6px;
            background-color: #151621;
        }
        QListWidget {
            border: none;
        }
        QListWidget::item {
            padding: 10px;
        }
        QListWidget::item:selected {
            background-color: rgba(21, 244, 208, 0.35);
        }
        QSlider::groove:horizontal {
            height: 6px;
            background: #222634;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #15f4d0;
            width: 18px;
            margin: -7px 0;
            border-radius: 9px;
        }
        QTextEdit {
            background-color: #11131b;
        }
        QToolBar {
            spacing: 12px;
            border-bottom: 1px solid #1f2a30;
        }
        QStatusBar {
            background-color: #0d0f16;
        }
        """
    )


class AsyncJob(QRunnable):
    """Lightweight wrapper that executes a callable within the global thread pool."""

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:  # pragma: no cover - executed in worker threads
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # pragma: no cover - log unexpected errors
            LOGGER.exception("Async job failed: %s", exc)


@dataclass
class ResonanceProfile:
    """Active targeting profile used by the resonance routines."""

    label: str
    target: str
    vector: str
    duration: int
    intensity: int
    proxies: List[str] = field(default_factory=list)
    notes: str = ""


class ResonanceController(QObject):
    """Backend facade that simulates the AinSOFT resonance laboratory features."""

    log_emitted = pyqtSignal(str, str)
    metrics_updated = pyqtSignal(dict)
    profile_updated = pyqtSignal(ResonanceProfile)

    def __init__(self) -> None:
        super().__init__()
        self._active_profile: Optional[ResonanceProfile] = None
        self._metrics: Dict[str, Any] = {
            "pps": 0,
            "bandwidth": 0.0,
            "proxies": 0,
            "success_rate": 0.0,
            "entropy": 0.0,
        }
        self._history: List[ResonanceProfile] = []
        self._stop_event = threading.Event()

    # --- Logging helpers -------------------------------------------------
    def _log(self, level: str, message: str) -> None:
        LOGGER.log(getattr(logging, level.upper(), logging.INFO), message)
        self.log_emitted.emit(level, message)

    # --- Profile Management ----------------------------------------------
    def stage_profile(self, profile: ResonanceProfile) -> None:
        """Set the active profile and notify listeners."""

        self._active_profile = profile
        self.profile_updated.emit(profile)
        self._log("info", f"Profile '{profile.label}' armed for {profile.target}")

    def current_profile(self) -> Optional[ResonanceProfile]:
        return self._active_profile

    # --- Resonance Execution --------------------------------------------
    def launch_resonance(self) -> None:
        """Execute the resonance sweep using the staged profile."""

        profile = self._active_profile
        if not profile:
            self._log("warning", "No active profile. Stage a target before firing.")
            return

        self._stop_event.clear()
        self._log(
            "info",
            f"Igniting resonance sweep at {profile.target} via {profile.vector} for {profile.duration}s",
        )
        for tick in range(profile.duration):
            if self._stop_event.is_set():
                self._log("warning", "Resonance sweep aborted by operator.")
                break
            simulated_pps = random.randint(200_000, 350_000) * profile.intensity
            simulated_bandwidth = simulated_pps * 0.002
            simulated_success = 0.8 + random.random() * 0.2
            simulated_entropy = 0.3 + random.random() * 0.4
            self._metrics.update(
                {
                    "pps": simulated_pps,
                    "bandwidth": simulated_bandwidth,
                    "proxies": len(profile.proxies),
                    "success_rate": simulated_success,
                    "entropy": simulated_entropy,
                }
            )
            self.metrics_updated.emit(self._metrics.copy())
            self._log("debug", f"Tick {tick + 1}/{profile.duration}: {simulated_pps:,}pps")
            time.sleep(1)
        else:
            self._log("success", "Resonance sweep completed. Analyze telemetry for artifacts.")

        self._history.append(profile)

    def abort_resonance(self) -> None:
        """Signal the worker loop to stop."""

        if self._stop_event.is_set():
            return
        self._stop_event.set()
        self._log("warning", "Operator requested immediate shutdown.")

    # --- Reconnaissance --------------------------------------------------
    def quick_probe(self, target: str, vector: str) -> Dict[str, Any]:
        """Simulate a reconnaissance probe against a target."""

        latency = random.uniform(40, 140)
        exposure = random.uniform(0.15, 0.9)
        surface = random.choice([
            "Load Balancer",
            "API Gateway",
            "Edge WAF",
            "Legacy Stack",
        ])
        self._log("info", f"Recon report for {target}: {surface}, latency {latency:.1f}ms")
        return {
            "target": target,
            "vector": vector,
            "latency": latency,
            "surface": surface,
            "recommendation": "Use burst mode with adaptive jitter" if exposure > 0.5 else "Use phantom pattern",
        }

    # --- Proxy Routines --------------------------------------------------
    def import_proxies(self, path: Path) -> List[str]:
        """Load proxies from a JSON or text list."""

        self._log("info", f"Loading proxy relay list from {path}")
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text())
            proxies = [str(item) for item in data]
        else:
            proxies = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        self._log("debug", f"Loaded {len(proxies)} proxies")
        return proxies

    def export_profile(self, profile: ResonanceProfile, path: Path) -> None:
        """Persist the profile to disk."""

        self._log("info", f"Exporting profile '{profile.label}' -> {path}")
        path.write_text(json.dumps(profile.__dict__, indent=2))

    def list_history(self) -> List[ResonanceProfile]:
        return list(self._history)


class LogConsole(QTextEdit):
    """Colored log console that differentiates info, warning, and errors."""

    LEVEL_COLORS = {
        "debug": QColor("#7ddcf4"),
        "info": QColor("#15f4d0"),
        "warning": QColor("#f5a623"),
        "error": QColor("#ff4d4f"),
        "critical": QColor("#ff4d4f"),
        "success": QColor("#7dffb3"),
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(160)
        self.setWordWrapMode(QTextOption.WrapMode.WordWrap)

    def append_entry(self, level: str, message: str) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(self.LEVEL_COLORS.get(level, QColor("#f5f5f7")))
        self.setCurrentCharFormat(fmt)
        self.append(f"[{level.upper()}] {message}")
        self.moveCursor(QTextCursor.MoveOperation.End)


class ResonanceWindow(QMainWindow):
    """Main window for the resonance pentesting console."""

    def __init__(self, controller: ResonanceController) -> None:
        super().__init__()
        self.controller = controller
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("AinSOFT Resonance Console")
        self.setMinimumSize(1280, 720)
        self._setup_toolbar()
        self._setup_layout()
        self._connect_signals()
        self._start_metrics_timer()

    # ------------------------------------------------------------------ UI
    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Primary Actions")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self.fire_button = QPushButton("Engage Resonance Sweep")
        self.fire_button.clicked.connect(self._on_launch)
        self.fire_button.setToolTip("Execute the staged resonance pattern against the target")
        toolbar.addWidget(self.fire_button)

        self.abort_button = QPushButton("Abort")
        self.abort_button.clicked.connect(self.controller.abort_resonance)
        self.abort_button.setToolTip("Abort the active sweep immediately")
        toolbar.addWidget(self.abort_button)

        self.quick_probe_button = QPushButton("Recon Ping")
        self.quick_probe_button.clicked.connect(self._on_quick_probe)
        self.quick_probe_button.setToolTip("Run a reconnaissance probe for the staged target")
        toolbar.addWidget(self.quick_probe_button)

    def _setup_layout(self) -> None:
        central = QWidget()
        root_layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        # Navigation column
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(12)

        search_label = QLabel("Navigate Modules")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        search_label.setFont(font)
        nav_layout.addWidget(search_label)

        self.module_list = QListWidget()
        self.module_list.setAlternatingRowColors(True)
        self.module_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        nav_layout.addWidget(self.module_list)

        splitter.addWidget(nav_container)
        splitter.setStretchFactor(0, 1)

        # Main stack
        self.stack = QStackedWidget()
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 3)

        # Build modules
        self._modules: List[Tuple[str, QWidget]] = [
            ("Dashboard", self._build_dashboard()),
            ("Target Acquisition", self._build_target_module()),
            ("Load Composer", self._build_pattern_module()),
            ("Proxy Network", self._build_proxy_module()),
            ("Telemetry", self._build_telemetry_module()),
            ("Engagement Logs", self._build_log_module()),
        ]
        for idx, (title, widget) in enumerate(self._modules):
            item = QListWidgetItem(title)
            self.module_list.addItem(item)
            self.stack.addWidget(widget)
            if idx == 0:
                self.module_list.setCurrentRow(0)

        self.module_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        # Status bar
        status = QStatusBar()
        self.setStatusBar(status)
        self.status_target = QLabel("Target: --")
        self.status_pattern = QLabel("Pattern: --")
        status.addWidget(self.status_target)
        status.addPermanentWidget(self.status_pattern)

    def _build_dashboard(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(16)

        status_box = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_box)
        self.status_overview = QLabel("No active profile")
        self.status_overview.setWordWrap(True)
        status_layout.addWidget(self.status_overview)
        layout.addWidget(status_box, 0, 0)

        quick_box = QGroupBox("Quick Actions")
        quick_layout = QVBoxLayout(quick_box)
        prep_button = QPushButton("Stage Default Load Profile")
        prep_button.clicked.connect(self._on_stage_default)
        quick_layout.addWidget(prep_button)
        save_button = QPushButton("Export Active Profile")
        save_button.clicked.connect(self._on_export_profile)
        quick_layout.addWidget(save_button)
        load_button = QPushButton("Import Profile JSON")
        load_button.clicked.connect(self._on_import_profile)
        quick_layout.addWidget(load_button)
        layout.addWidget(quick_box, 0, 1)

        alerts_box = QGroupBox("Alerts")
        alerts_layout = QVBoxLayout(alerts_box)
        self.alerts_label = QLabel("Standing by for telemetry anomalies...")
        self.alerts_label.setWordWrap(True)
        alerts_layout.addWidget(self.alerts_label)
        layout.addWidget(alerts_box, 1, 0, 1, 2)

        return widget

    def _build_target_module(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        profile_box = QGroupBox("Target Parameters")
        form = QFormLayout(profile_box)
        self.profile_label_input = QLineEdit()
        self.profile_label_input.setPlaceholderText("Engagement codename")
        form.addRow("Profile Label", self.profile_label_input)

        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("IPv4 / IPv6 / Hostname")
        form.addRow("Target Address", self.target_input)

        self.vector_combo = QComboBox()
        self.vector_combo.addItems([
            "Volumetric Burst",
            "Protocol Flood",
            "Application Cascade",
            "Phantom Jitter",
        ])
        form.addRow("Vector", self.vector_combo)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 600)
        self.duration_spin.setValue(60)
        self.duration_spin.setSuffix(" s")
        form.addRow("Duration", self.duration_spin)

        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(1, 10)
        self.intensity_slider.setValue(4)
        form.addRow("Intensity", self.intensity_slider)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Engagement notes, expected defenses, etc.")
        form.addRow("Notes", self.notes_input)

        layout.addWidget(profile_box)

        stage_button = QPushButton("Arm Target Profile")
        stage_button.clicked.connect(self._on_stage_profile)
        layout.addWidget(stage_button)

        return widget

    def _build_pattern_module(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        composer_box = QGroupBox("Load Pattern Composer")
        form = QFormLayout(composer_box)

        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Adaptive Burst",
            "Low-and-Slow",
            "Randomized Edge",
            "Amplification Relay",
        ])
        form.addRow("Pattern", self.pattern_combo)

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 4096)
        self.threads_spin.setValue(256)
        form.addRow("Threads", self.threads_spin)

        self.jitter_slider = QSlider(Qt.Orientation.Horizontal)
        self.jitter_slider.setRange(0, 100)
        self.jitter_slider.setValue(12)
        form.addRow("Jitter", self.jitter_slider)

        self.payload_combo = QComboBox()
        self.payload_combo.addItems([
            "HTTP/2 Rapid Reset",
            "TLS Renegotiation",
            "UDP Reflection",
            "Custom Script",
        ])
        form.addRow("Payload", self.payload_combo)

        layout.addWidget(composer_box)

        simulate_button = QPushButton("Simulate Pattern")
        simulate_button.clicked.connect(self._on_simulate_pattern)
        layout.addWidget(simulate_button)

        return widget

    def _build_proxy_module(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        proxy_box = QGroupBox("Proxy Relay Network")
        vbox = QVBoxLayout(proxy_box)
        self.proxy_list = QTextEdit()
        self.proxy_list.setPlaceholderText("host:port one per line")
        vbox.addWidget(self.proxy_list)

        buttons = QHBoxLayout()
        import_button = QPushButton("Import List")
        import_button.clicked.connect(self._on_import_proxies)
        buttons.addWidget(import_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.proxy_list.clear)
        buttons.addWidget(clear_button)
        vbox.addLayout(buttons)

        layout.addWidget(proxy_box)
        return widget

    def _build_telemetry_module(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        if MPL_AVAILABLE:
            figure = Figure(figsize=(5, 3))
            self.telemetry_axes = figure.add_subplot(111)
            self.telemetry_axes.set_facecolor("#11131b")
            self.telemetry_axes.tick_params(colors="#f5f5f7")
            self.telemetry_axes.set_title("Packets per Second", color="#f5f5f7")
            self.telemetry_canvas = FigureCanvasQTAgg(figure)
            layout.addWidget(self.telemetry_canvas)
        else:
            fallback = QLabel("Install matplotlib for live telemetry charts.")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(fallback)
            self.telemetry_axes = None  # type: ignore
            self.telemetry_canvas = None  # type: ignore

        metrics_box = QGroupBox("Live Metrics")
        metrics_layout = QFormLayout(metrics_box)
        self.metric_pps = QLabel("0")
        metrics_layout.addRow("Packets/s", self.metric_pps)
        self.metric_bandwidth = QLabel("0 Mbps")
        metrics_layout.addRow("Bandwidth", self.metric_bandwidth)
        self.metric_success = QLabel("0%")
        metrics_layout.addRow("Success Rate", self.metric_success)
        self.metric_entropy = QLabel("0.0")
        metrics_layout.addRow("Entropy", self.metric_entropy)
        self.metric_proxies = QLabel("0")
        metrics_layout.addRow("Proxy Relays", self.metric_proxies)

        layout.addWidget(metrics_box)
        return widget

    def _build_log_module(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        self.log_console = LogConsole()
        layout.addWidget(self.log_console)

        history_button = QPushButton("Export Engagement History")
        history_button.clicked.connect(self._on_export_history)
        layout.addWidget(history_button)

        return widget

    def _connect_signals(self) -> None:
        self.controller.log_emitted.connect(self.log_console.append_entry)
        self.controller.metrics_updated.connect(self._on_metrics)
        self.controller.profile_updated.connect(self._on_profile_update)

    def _start_metrics_timer(self) -> None:
        self.metrics_series: List[int] = []
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.setInterval(1500)
        self.telemetry_timer.timeout.connect(self._refresh_telemetry)
        self.telemetry_timer.start()

    # ---------------------------------------------------------- Controller
    def _on_stage_profile(self) -> None:
        label = self.profile_label_input.text().strip() or "Untitled Engagement"
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Missing Target", "Provide a target address before arming.")
            return
        vector = self.vector_combo.currentText()
        duration = self.duration_spin.value()
        intensity = self.intensity_slider.value()
        proxies = [line.strip() for line in self.proxy_list.toPlainText().splitlines() if line.strip()]
        profile = ResonanceProfile(
            label=label,
            target=target,
            vector=vector,
            duration=duration,
            intensity=intensity,
            proxies=proxies,
            notes=self.notes_input.toPlainText().strip(),
        )
        self.controller.stage_profile(profile)

    def _on_launch(self) -> None:
        job = AsyncJob(self.controller.launch_resonance)
        self.thread_pool.start(job)

    def _on_quick_probe(self) -> None:
        profile = self.controller.current_profile()
        if not profile:
            QMessageBox.information(self, "No Target", "Stage a profile to probe its defenses.")
            return
        report = self.controller.quick_probe(profile.target, profile.vector)
        QMessageBox.information(
            self,
            "Recon Report",
            (
                f"Target: {report['target']}\n"
                f"Vector: {report['vector']}\n"
                f"Latency: {report['latency']:.1f} ms\n"
                f"Surface: {report['surface']}\n"
                f"Recommendation: {report['recommendation']}"
            ),
        )

    def _on_stage_default(self) -> None:
        self.profile_label_input.setText("Baseline Sweep")
        self.target_input.setText("198.51.100.42")
        self.vector_combo.setCurrentText("Volumetric Burst")
        self.duration_spin.setValue(45)
        self.intensity_slider.setValue(5)
        self.notes_input.setText("TODO: Replace with live intel from reconnaissance module.")
        QMessageBox.information(self, "Profile Loaded", "Default resonance profile prepared.")

    def _on_export_profile(self) -> None:
        profile = self.controller.current_profile()
        if not profile:
            QMessageBox.warning(self, "Nothing to Export", "Stage a profile before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Profile", filter="JSON (*.json)")
        if not path:
            return
        self.controller.export_profile(profile, Path(path))
        QMessageBox.information(self, "Export Complete", f"Profile saved to {path}")

    def _on_import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Profile", filter="JSON (*.json)")
        if not path:
            return
        data = json.loads(Path(path).read_text())
        profile = ResonanceProfile(
            label=data.get("label", "Imported Profile"),
            target=data.get("target", ""),
            vector=data.get("vector", "Volumetric Burst"),
            duration=int(data.get("duration", 60)),
            intensity=int(data.get("intensity", 4)),
            proxies=list(data.get("proxies", [])),
            notes=data.get("notes", ""),
        )
        self.profile_label_input.setText(profile.label)
        self.target_input.setText(profile.target)
        idx = max(0, self.vector_combo.findText(profile.vector))
        self.vector_combo.setCurrentIndex(idx)
        self.duration_spin.setValue(profile.duration)
        self.intensity_slider.setValue(profile.intensity)
        self.proxy_list.setPlainText("\n".join(profile.proxies))
        self.notes_input.setPlainText(profile.notes)
        self.controller.stage_profile(profile)

    def _on_simulate_pattern(self) -> None:
        pattern = self.pattern_combo.currentText()
        threads = self.threads_spin.value()
        jitter = self.jitter_slider.value()
        payload = self.payload_combo.currentText()
        QMessageBox.information(
            self,
            "Simulation",
            (
                f"Pattern: {pattern}\n"
                f"Threads: {threads}\n"
                f"Jitter: ±{jitter}%\n"
                f"Payload: {payload}\n\n"
                "TODO: Integrate with AinSOFT load composer backend."
            ),
        )

    def _on_import_proxies(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Proxies", filter="Proxy Lists (*.json *.txt)")
        if not path:
            return
        proxies = self.controller.import_proxies(Path(path))
        self.proxy_list.setPlainText("\n".join(proxies))
        QMessageBox.information(self, "Proxies Loaded", f"Loaded {len(proxies)} proxies")

    def _on_export_history(self) -> None:
        history = self.controller.list_history()
        if not history:
            QMessageBox.information(self, "No History", "Run at least one sweep to generate history.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export History", filter="JSON (*.json)")
        if not path:
            return
        Path(path).write_text(
            json.dumps([profile.__dict__ for profile in history], indent=2)
        )
        QMessageBox.information(self, "Export Complete", f"Engagement history saved to {path}")

    def _on_metrics(self, metrics: Dict[str, Any]) -> None:
        self.metric_pps.setText(f"{metrics['pps']:,}")
        self.metric_bandwidth.setText(f"{metrics['bandwidth'] / 1_000:.2f} Gbps")
        self.metric_success.setText(f"{metrics['success_rate'] * 100:.1f}%")
        self.metric_entropy.setText(f"{metrics['entropy']:.2f}")
        self.metric_proxies.setText(str(metrics['proxies']))
        self.metrics_series.append(metrics["pps"])
        if len(self.metrics_series) > 20:
            self.metrics_series.pop(0)

    def _refresh_telemetry(self) -> None:
        if not MPL_AVAILABLE or not getattr(self, "telemetry_axes", None):
            return
        self.telemetry_axes.clear()
        self.telemetry_axes.set_facecolor("#11131b")
        self.telemetry_axes.plot(self.metrics_series, color="#15f4d0", linewidth=2)
        self.telemetry_axes.set_title("Packets per Second", color="#f5f5f7")
        self.telemetry_axes.tick_params(colors="#f5f5f7")
        self.telemetry_canvas.draw()

    def _on_profile_update(self, profile: ResonanceProfile) -> None:
        self.status_overview.setText(
            (
                f"Targeting <b>{profile.target}</b> with <b>{profile.vector}</b><br>"
                f"Duration: {profile.duration}s | Intensity: {profile.intensity}"
                f" | Relays: {len(profile.proxies)}"
            )
        )
        self.status_target.setText(f"Target: {profile.target}")
        self.status_pattern.setText(f"Vector: {profile.vector}")

    # -------------------------------------------------------------- Logging
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.controller.abort_resonance()
        super().closeEvent(event)


def run() -> int:
    """Entry point used by external callers to launch the resonance console."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    apply_resonance_palette(app)
    controller = ResonanceController()
    window = ResonanceWindow(controller)
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    raise SystemExit(run())


# ---------------------------------------------------------------------------
# Installation & Execution
# ```bash
# pip install -r requirements.txt
# python -m ainsoft.interfaces.resonance_gui
# ```
# ---------------------------------------------------------------------------
