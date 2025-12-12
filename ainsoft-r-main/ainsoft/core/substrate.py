"""Data substrate and spiral memory utilities for AinSOFT.

This module manages cyclic storage of response data while exposing
an iteration primitive that can later be extended to provide true
spiral-order traversal semantics.
"""

from __future__ import annotations

from typing import Any, Iterable, List


class Substrate:
    """Bounded in-memory buffer that stores response artefacts."""

    def __init__(self, maxlen: int = 256):
        self.maxlen = maxlen
        self.memory: List[Any] = []

    def store(self, data: Any) -> None:
        """Store *data* in the substrate, keeping the buffer bounded."""

        if len(self.memory) >= self.maxlen:
            self.memory.pop(0)
        self.memory.append(data)

    def iterate_spiral(self) -> Iterable[Any]:
        """Return an iterable over the stored data.

        The actual spiral ordering can be implemented once the
        surrounding system requires it. For now, return the stored
        samples in insertion order to keep the behaviour deterministic
        for tests.
        """

        return list(self.memory)

