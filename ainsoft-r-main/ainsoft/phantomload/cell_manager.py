"""Cell management utilities for phantomload simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
import uuid
from typing import Dict, Iterable, List, Optional

import numpy as np

from ainsoft.pipeline.web3suite import MutationEngine, SeedClusterEngine, SeedDNAEngine


@dataclass
class PhantomCell:
    """Represents a phantomload cell tied to a seed geometry."""

    cell_id: str
    geometry: np.ndarray
    seed_phrase: str
    cluster: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, object] = field(default_factory=dict)

    def position(self) -> List[float]:
        """Return a 3D position derived from the 5D geometry."""

        base = np.asarray(self.geometry, dtype=float)
        if base.size < 3:
            base = np.pad(base, (0, 3 - base.size))
        return base[:3].tolist()

    def score(self) -> float:
        """Return a magnitude-based score used for colouring."""

        base = np.asarray(self.geometry, dtype=float)
        return float(np.linalg.norm(base))

    def snapshot(self) -> Dict[str, object]:
        """Return a serialisable representation of the cell."""

        return {
            "id": self.cell_id,
            "position": self.position(),
            "score": self.score(),
            "cluster": self.cluster,
            "created_at": self.created_at,
            "seed": self.seed_phrase,
            "metadata": dict(self.metadata),
        }


class PhantomCellManager:
    """Manage phantom cells using seed-based geometry encoding."""

    def __init__(
        self,
        dna_engine: Optional[SeedDNAEngine] = None,
        mutation_engine: Optional[MutationEngine] = None,
        cluster_engine: Optional[SeedClusterEngine] = None,
    ) -> None:
        self.dna_engine = dna_engine or SeedDNAEngine()
        self.mutation_engine = mutation_engine or MutationEngine(self.dna_engine)
        self.cluster_engine = cluster_engine or SeedClusterEngine()
        self.cells: Dict[str, PhantomCell] = {}

    def spawn_cells(self, count: int, base_phrase: str, *, mutate: bool = True) -> List[PhantomCell]:
        """Spawn ``count`` cells using deterministic or mutated seeds."""

        created: List[PhantomCell] = []
        for index in range(count):
            phrase = base_phrase
            if mutate:
                mutated = self.mutation_engine.generate_mutant(f"{base_phrase}-{index}")
                geometry = np.asarray(mutated, dtype=float)
                phrase = f"{base_phrase}-{index}"
            else:
                geometry = self.dna_engine.encode(f"{base_phrase}-{index}")
            cell_id = uuid.uuid4().hex
            cell = PhantomCell(cell_id=cell_id, geometry=geometry, seed_phrase=phrase)
            self.cells[cell_id] = cell
            created.append(cell)
        self.assign_clusters()
        return created

    def assign_clusters(self) -> None:
        """Assign cluster labels using the configured engine."""

        if not self.cells:
            return
        seeds = [cell.geometry for cell in self.cells.values()]
        labels = self.cluster_engine.cluster_seeds(seeds)
        for cell, label in zip(self.cells.values(), labels):
            cell.cluster = label

    def to_mesh(self, *, view: str = "traffic") -> Dict[str, object]:
        """Return a lightweight mesh snapshot for visualisation."""

        nodes = [cell.snapshot() for cell in self.cells.values()]
        edges: List[Dict[str, object]] = []
        cell_ids = list(self.cells.keys())
        for idx, src in enumerate(cell_ids):
            dst = cell_ids[(idx + 1) % len(cell_ids)]
            if src == dst:
                continue
            distance = float(
                np.linalg.norm(self.cells[src].geometry - self.cells[dst].geometry)
            )
            edges.append({"source": src, "target": dst, "weight": distance})
        return {"view": view, "nodes": nodes, "edges": edges}

    def reset(self) -> None:
        """Remove all cells."""

        self.cells.clear()

    def cell_count(self) -> int:
        """Return the number of active cells."""

        return len(self.cells)

    def iter_cells(self) -> Iterable[PhantomCell]:
        """Iterate over the registered cells."""

        return list(self.cells.values())
