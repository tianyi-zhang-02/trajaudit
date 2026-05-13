"""Filesystem diff utilities for Layer 1.

The :class:`FSDiffer` consumes two snapshots of a workspace — the
initial state the benchmark shipped, and the final state the agent
left behind — and returns a structured description of every file
added, removed, or modified, classified by which subtree of the
workspace it touched (source vs. tests vs. config vs.
harness-internal).

Path classification is benchmark-specific; the benchmark adapter
provides a :class:`PathClassifier` that this module consults.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class PathClass(StrEnum):
    """Coarse classification of a workspace path."""

    SOURCE = "source"
    TEST = "test"
    CONFIG = "config"
    HARNESS_INTERNAL = "harness_internal"
    BUILD_ARTIFACT = "build_artifact"
    UNKNOWN = "unknown"


class FileChange(BaseModel):
    """A single file change between two workspace snapshots."""

    path: Path
    classification: PathClass
    added: bool = False
    removed: bool = False
    modified: bool = False
    size_delta: int = 0


class PathClassifier(Protocol):
    """Benchmark-supplied path classifier."""

    def classify(self, path: Path) -> PathClass: ...


class FSDiffer:
    """Compute structured filesystem diffs between two workspace snapshots."""

    def __init__(self, classifier: PathClassifier) -> None:
        self.classifier = classifier

    def diff(
        self,
        before: dict[Path, bytes],
        after: dict[Path, bytes],
    ) -> list[FileChange]:
        """Return the set of file-level changes between two snapshots."""
        raise NotImplementedError("Phase 3: implement workspace diff.")
