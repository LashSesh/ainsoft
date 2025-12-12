"""Mesh-layer blueprints for AinSOFT's triangulation workflows."""

from __future__ import annotations

import json
import math
import pickle
import random
import statistics
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:  # SciPy is optional; fall back to simple numpy logic when unavailable.
    from scipy.spatial import Delaunay, KDTree  # type: ignore
except Exception:  # pragma: no cover - absence of SciPy is expected in tests
    Delaunay = None  # type: ignore[assignment]
    KDTree = None  # type: ignore[assignment]


class StructuredAuditLogger:
    """Writes audit events to a JSONL file for later inspection."""

    def __init__(self, filename: str = "audit_log.jsonl"):
        self.filename = filename

    def log(self, record: Mapping[str, Any]) -> None:
        with open(self.filename, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


class OperatorRegistry:
    """Registry used to plug in mesh operators (solve/gate/etc.)."""

    def __init__(self) -> None:
        self._operators: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self._operators[name] = func

    def get(self, name: str) -> Optional[Callable[..., Any]]:
        return self._operators.get(name)


class PointCloud:
    """Represents an N-dimensional point cloud (default 5D)."""

    def __init__(self, points: Optional[Iterable[Sequence[float]]] = None, dimensions: int = 5):
        self.dimensions = dimensions
        if np is not None:
            if points is None:
                iterable: Iterable[Sequence[float]] = []
            elif isinstance(points, np.ndarray):
                iterable = points.tolist()
            else:
                iterable = list(points)
            initial = np.array(iterable, dtype=float)
            if initial.ndim == 1 and initial.size > 0:
                initial = initial.reshape(1, -1)
            if initial.size == 0:
                initial = np.zeros((0, dimensions), dtype=float)
            self.points: Any = initial
        else:
            rows = [list(map(float, row)) for row in (points or [])]
            for row in rows:
                if len(row) != dimensions:
                    dimensions = len(row)
            self.points = rows

    def add(self, point: Sequence[float]) -> None:
        if np is not None:
            arr = np.array(point, dtype=float)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            self.points = np.vstack([self.points, arr]) if self.points.size else arr
        else:
            row = [float(value) for value in point]
            self.points.append(row)

    def as_array(self) -> Any:
        return self.points


@dataclass
class MeshAuditEvent:
    event: str
    info: MutableMapping[str, Any]


class MeshBuilder:
    """Constructs meshes (Delaunay or kNN) from a :class:`PointCloud`."""

    def __init__(
        self,
        pointcloud: PointCloud,
        *,
        mode: str = "delaunay",
        k: int = 5,
        logger: Optional[StructuredAuditLogger] = None,
    ) -> None:
        self.pointcloud = pointcloud
        self.mode = mode
        self.k = max(1, int(k))
        self.logger = logger
        self.tri: Any = None
        self.edges: List[Tuple[int, int]] = []
        self.edge_scores: Dict[Tuple[int, int], float] = {}
        self.audit_log: List[MeshAuditEvent] = []

    def build(self) -> None:
        pts = self.pointcloud.as_array()
        if len(pts) <= 1:
            self.edges = []
            self._audit("build", {"edges": 0, "reason": "insufficient_points"})
            return

        if self.mode == "delaunay":
            if Delaunay is None:
                raise RuntimeError("scipy is required for 'delaunay' mesh mode")
            if np is None:
                raise RuntimeError("numpy is required for 'delaunay' mesh mode")
            if pts.shape[0] <= pts.shape[1]:
                self.edges = []
                self._audit("build", {"edges": 0, "reason": "degenerate_simplex"})
                return
            self.tri = Delaunay(pts)  # type: ignore[arg-type]
            self.edges = self._extract_edges_from_simplices(self.tri.simplices)
        elif self.mode == "knn":
            self.edges = self._build_knn_edges(pts)
        else:  # pragma: no cover - defensive branch
            raise ValueError(f"Unknown mesh mode: {self.mode}")

        self._audit("build", {"edges": len(self.edges), "mode": self.mode})

    def _build_knn_edges(self, pts: Any) -> List[Tuple[int, int]]:
        edges: set[Tuple[int, int]] = set()
        count = len(pts)
        k = min(self.k, count - 1)
        if k <= 0:
            return []

        if np is not None and KDTree is not None:
            tree = KDTree(pts)
            for idx, point in enumerate(pts):
                _dists, indices = tree.query(point, k=k + 1)
                for neighbour in indices[1:]:
                    edge = tuple(sorted((int(idx), int(neighbour))))
                    edges.add(edge)
        else:
            for idx, point in enumerate(pts):
                distances = [math.dist(point, other) for other in pts]
                nearest = sorted(range(len(distances)), key=lambda n: distances[n])[1 : k + 1]
                for neighbour in nearest:
                    edge = tuple(sorted((int(idx), int(neighbour))))
                    edges.add(edge)

        return sorted(edges)

    def _extract_edges_from_simplices(self, simplices: Any) -> List[Tuple[int, int]]:
        edges: set[Tuple[int, int]] = set()
        for simplex in simplices:
            for i in range(len(simplex)):
                for j in range(i + 1, len(simplex)):
                    edge = tuple(sorted((int(simplex[i]), int(simplex[j]))))
                    edges.add(edge)
        return sorted(edges)

    def weight_edges(self, score_func: Callable[[Sequence[float], Sequence[float]], float]) -> None:
        pts = self.pointcloud.as_array()
        self.edge_scores.clear()
        for i, j in self.edges:
            score = float(score_func(pts[i], pts[j]))
            self.edge_scores[(i, j)] = score
        self._audit("weight_edges", {"edges_weighted": len(self.edges)})

    def audit_trail(self) -> List[MeshAuditEvent]:
        return list(self.audit_log)

    def _audit(self, event: str, info: Dict[str, Any]) -> None:
        record = MeshAuditEvent(event=event, info=info)
        self.audit_log.append(record)
        if self.logger:
            self.logger.log({"event": event, "info": info})


class TopologyGuard:
    """Performs simple coherence checks on a mesh."""

    def __init__(self, meshbuilder: MeshBuilder) -> None:
        self.meshbuilder = meshbuilder

    def check_coherence(self) -> bool:
        pts = self.meshbuilder.pointcloud.as_array()
        if len(pts) == 0:
            return False
        connected: set[int] = set()
        for i, j in self.meshbuilder.edges:
            connected.add(i)
            connected.add(j)
        return len(connected) == len(pts)

    def betti_numbers(self) -> List[int]:
        return [1] if self.check_coherence() else [0]


class EntropyControl:
    """Tracks mesh complexity using a logarithmic entropy score."""

    def __init__(self, meshbuilder: MeshBuilder, max_entropy: float = 10.0) -> None:
        self.meshbuilder = meshbuilder
        self.max_entropy = float(max_entropy)

    def entropy(self) -> float:
        num_points = len(self.meshbuilder.pointcloud.as_array())
        num_edges = len(self.meshbuilder.edges)
        if np is not None:
            return float(np.log2(1 + num_points) + np.log2(1 + num_edges))
        return math.log2(1 + num_points) + math.log2(1 + num_edges)

    def is_stable(self) -> bool:
        return self.entropy() < self.max_entropy


def solve(meshbuilder: MeshBuilder) -> None:
    """Removes edges with a score below the median."""

    scores = list(meshbuilder.edge_scores.values())
    if not scores:
        return
    if np is not None:
        median = float(np.median(scores))
    else:
        median = float(statistics.median(scores))
    to_remove = [edge for edge, score in meshbuilder.edge_scores.items() if score < median]
    for edge in to_remove:
        if edge in meshbuilder.edges:
            meshbuilder.edges.remove(edge)
        meshbuilder.edge_scores.pop(edge, None)
    meshbuilder._audit("solve", {"removed": len(to_remove), "median": median})


def gate(meshbuilder: MeshBuilder, threshold: float = 0.7) -> None:
    """Keeps only edges that exceed the given score threshold."""

    to_remove = [edge for edge, score in meshbuilder.edge_scores.items() if score < threshold]
    for edge in to_remove:
        if edge in meshbuilder.edges:
            meshbuilder.edges.remove(edge)
        meshbuilder.edge_scores.pop(edge, None)
    meshbuilder._audit("gate", {"removed": len(to_remove), "threshold": threshold})


def coagula(meshbuilder: MeshBuilder) -> Dict[int, int]:
    """Merges highly resonant nodes into clusters and returns their labels."""

    pts = meshbuilder.pointcloud.as_array()
    labels: Dict[int, int] = {i: i for i in range(len(pts))}
    for i, j in meshbuilder.edges:
        if meshbuilder.edge_scores.get((i, j), 0.0) > 0.9:
            label = min(labels[i], labels[j])
            labels[i] = label
            labels[j] = label
    meshbuilder._audit("coagula", {"clusters": len(set(labels.values()))})
    return labels


def expand(meshbuilder: MeshBuilder, grad_func: Callable[[Sequence[float]], Sequence[float]], step: float = 0.1) -> None:
    """Moves points along a gradient direction by a fixed step."""

    pts = meshbuilder.pointcloud.as_array()
    if len(pts) == 0:
        return
    if np is not None:
        gradients = np.array([grad_func(pt) for pt in pts], dtype=float)
        if gradients.shape != pts.shape:
            raise ValueError("Gradient function must return vectors of the same dimension as the points")
        meshbuilder.pointcloud.points = pts + step * gradients
    else:
        updated = []
        for point in pts:
            grad = list(map(float, grad_func(point)))
            if len(grad) != len(point):
                raise ValueError("Gradient function must return vectors of the same dimension as the points")
            updated.append([p + step * g for p, g in zip(point, grad)])
        meshbuilder.pointcloud.points = updated
    meshbuilder._audit("expand", {"step": step})


class MeshLayer:
    """High-level orchestrator for AinSOFT mesh pipelines."""

    def __init__(
        self,
        input_points: Iterable[Sequence[float]],
        *,
        mode: str = "delaunay",
        k: int = 5,
        logger: Optional[StructuredAuditLogger] = None,
        operator_registry: Optional[OperatorRegistry] = None,
    ) -> None:
        self.pointcloud = PointCloud(input_points)
        self.meshbuilder = MeshBuilder(self.pointcloud, mode=mode, k=k, logger=logger)
        self.topology_guard = TopologyGuard(self.meshbuilder)
        self.entropy_control = EntropyControl(self.meshbuilder)
        self.operator_registry = operator_registry or DEFAULT_OPERATOR_REGISTRY
        self.state: Dict[str, Any] = {}

    def build_mesh(self) -> None:
        self.meshbuilder.build()

    def weight_edges(self, score_func: Callable[[Sequence[float], Sequence[float]], float]) -> None:
        self.meshbuilder.weight_edges(score_func)

    def solve(self) -> None:
        operator = self.operator_registry.get("solve")
        if operator:
            operator(self.meshbuilder)

    def gate(self, threshold: float) -> None:
        operator = self.operator_registry.get("gate")
        if operator:
            operator(self.meshbuilder, threshold)

    def coagula(self) -> Dict[int, int]:
        operator = self.operator_registry.get("coagula")
        if operator:
            return operator(self.meshbuilder)
        return {}

    def expand(self, grad_func: Callable[[Sequence[float]], Sequence[float]], step: float = 0.1) -> None:
        operator = self.operator_registry.get("expand")
        if operator:
            operator(self.meshbuilder, grad_func, step)

    def check_topology(self) -> Tuple[bool, List[int]]:
        return self.topology_guard.check_coherence(), self.topology_guard.betti_numbers()

    def check_entropy(self) -> Tuple[bool, float]:
        return self.entropy_control.is_stable(), self.entropy_control.entropy()

    def audit(self) -> List[MeshAuditEvent]:
        return self.meshbuilder.audit_trail()

    def find_targets(
        self,
        targeting_func: Callable[[np.ndarray, List[Tuple[int, int]], Dict[Tuple[int, int], float]], Any],
    ) -> Any:
        pts = self.pointcloud.as_array()
        return targeting_func(pts, self.meshbuilder.edges, self.meshbuilder.edge_scores)

    def export_state(self, filename: str = "meshlayer_state.pkl") -> None:
        with open(filename, "wb") as handle:
            pickle.dump(self, handle)

    @staticmethod
    def import_state(filename: str = "meshlayer_state.pkl") -> "MeshLayer":
        with open(filename, "rb") as handle:
            return pickle.load(handle)

    def export_json(self, filename: str = "mesh.json") -> None:
        points = self.pointcloud.as_array()
        if np is not None:
            points_serialisable = points.tolist()
        else:
            points_serialisable = [list(map(float, row)) for row in points]
        mesh_data = {
            "points": points_serialisable,
            "edges": [list(edge) for edge in self.meshbuilder.edges],
            "edge_scores": {f"{edge[0]}-{edge[1]}": score for edge, score in self.meshbuilder.edge_scores.items()},
        }
        with open(filename, "w", encoding="utf-8") as handle:
            json.dump(mesh_data, handle)

    def print_stats(self) -> None:  # pragma: no cover - utility output
        print("Points:", len(self.pointcloud.as_array()))
        print("Edges:", len(self.meshbuilder.edges))
        print("Audit log (last 3):", self.audit()[-3:])


def example_score_func(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Example distance-based resonance score."""

    if np is not None:
        dist = float(np.linalg.norm(np.array(vec1, dtype=float) - np.array(vec2, dtype=float)))
    else:
        dist = math.dist([float(v) for v in vec1], [float(v) for v in vec2])
    return 1.0 / (1.0 + dist)


def example_grad_func(vec: Sequence[float]) -> np.ndarray:
    """Example gradient pointing towards the origin."""

    if np is not None:
        arr = np.array(vec, dtype=float)
        norm = np.linalg.norm(arr) + 1e-9
        return -arr / norm
    arr = [float(v) for v in vec]
    norm = math.sqrt(sum(value * value for value in arr)) + 1e-9
    return [-(value / norm) for value in arr]


def example_targeting_func(
    points: np.ndarray, edges: List[Tuple[int, int]], edge_scores: Dict[Tuple[int, int], float]
) -> Optional[int]:
    """Selects the node participating in the strongest edge."""

    if not edge_scores:
        return None
    best_edge = max(edge_scores.items(), key=lambda item: item[1])[0]
    return int(best_edge[0]) if best_edge else None


DEFAULT_OPERATOR_REGISTRY = OperatorRegistry()
DEFAULT_OPERATOR_REGISTRY.register("solve", solve)
DEFAULT_OPERATOR_REGISTRY.register("gate", gate)
DEFAULT_OPERATOR_REGISTRY.register("coagula", coagula)
DEFAULT_OPERATOR_REGISTRY.register("expand", expand)


def export_mesh_json(meshlayer: MeshLayer, filename: str = "mesh.json") -> None:
    meshlayer.export_json(filename)


def print_mesh_stats(meshlayer: MeshLayer) -> None:  # pragma: no cover - utility output
    meshlayer.print_stats()


def fuzz_meshlayer(
    n_tests: int = 10,
    *,
    dim: int = 5,
    n_points: int = 20,
    operator_registry: Optional[OperatorRegistry] = None,
) -> None:  # pragma: no cover - fuzz helper
    registry = operator_registry or DEFAULT_OPERATOR_REGISTRY
    for _ in range(n_tests):
        if np is not None:
            points = np.random.rand(n_points, dim)
        else:
            points = [[random.random() for _ in range(dim)] for _ in range(n_points)]
        layer = MeshLayer(points, mode="knn", k=min(5, n_points - 1), operator_registry=registry)
        layer.build_mesh()
        layer.weight_edges(example_score_func)
        layer.solve()
        layer.gate(0.5)
        layer.coagula()
        layer.expand(example_grad_func)


def create_mesh_app(
    meshlayer: MeshLayer,
    *,
    score_func: Callable[[Sequence[float], Sequence[float]], float] = example_score_func,
    grad_func: Callable[[Sequence[float]], Sequence[float]] = example_grad_func,
    export_path: Optional[str] = None,
):
    """Creates a FastAPI application for interacting with a :class:`MeshLayer`."""

    from fastapi import FastAPI

    app = FastAPI()

    @app.post("/mesh/build")
    def api_build() -> Dict[str, Any]:
        meshlayer.build_mesh()
        return {"status": "mesh built", "edges": len(meshlayer.meshbuilder.edges)}

    @app.post("/mesh/weight")
    def api_weight() -> Dict[str, Any]:
        meshlayer.weight_edges(score_func)
        return {"status": "edges weighted", "weighted": len(meshlayer.meshbuilder.edge_scores)}

    @app.post("/mesh/solve")
    def api_solve() -> Dict[str, Any]:
        meshlayer.solve()
        return {"status": "solved"}

    @app.post("/mesh/gate/{threshold}")
    def api_gate(threshold: float) -> Dict[str, Any]:
        meshlayer.gate(threshold)
        return {"status": "gated", "threshold": threshold}

    @app.post("/mesh/expand")
    def api_expand(step: float = 0.1) -> Dict[str, Any]:
        meshlayer.expand(grad_func, step=step)
        return {"status": "expanded", "step": step}

    @app.get("/mesh/edges")
    def api_edges() -> Dict[str, Any]:
        return {"edges": meshlayer.meshbuilder.edges}

    @app.get("/mesh/audit")
    def api_audit() -> Dict[str, Any]:
        return {"audit": [event.__dict__ for event in meshlayer.audit()]}

    @app.get("/mesh/entropy")
    def api_entropy() -> Dict[str, Any]:
        stable, entropy = meshlayer.check_entropy()
        return {"stable": stable, "entropy": entropy}

    @app.get("/mesh/topology")
    def api_topology() -> Dict[str, Any]:
        coherence, betti = meshlayer.check_topology()
        return {"coherent": coherence, "betti": betti}

    @app.get("/mesh/export")
    def api_export() -> Dict[str, Any]:
        filename = export_path or "mesh.json"
        meshlayer.export_json(filename)
        return {"status": "exported", "path": filename}

    return app


__all__ = [
    "StructuredAuditLogger",
    "OperatorRegistry",
    "PointCloud",
    "MeshBuilder",
    "MeshLayer",
    "MeshAuditEvent",
    "TopologyGuard",
    "EntropyControl",
    "solve",
    "gate",
    "coagula",
    "expand",
    "example_score_func",
    "example_grad_func",
    "example_targeting_func",
    "DEFAULT_OPERATOR_REGISTRY",
    "export_mesh_json",
    "print_mesh_stats",
    "fuzz_meshlayer",
    "create_mesh_app",
]
