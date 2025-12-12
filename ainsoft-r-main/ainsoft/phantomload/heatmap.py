"""Heatmap export helpers for phantomload analytics."""

from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np

from .cell_manager import PhantomCell


class HeatmapExporter:
    """Compute lightweight heatmap snapshots for dashboards and Unity."""

    def build(self, cells: Iterable[PhantomCell]) -> List[Dict[str, object]]:
        """Return a list of heatmap entries derived from cells."""

        entries: List[Dict[str, object]] = []
        for cell in cells:
            magnitude = np.linalg.norm(cell.geometry)
            entries.append(
                {
                    "id": cell.cell_id,
                    "cluster": cell.cluster,
                    "intensity": float(magnitude),
                    "position": cell.position(),
                }
            )
        return entries
