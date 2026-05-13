"""Benchmark adapter base class.

A :class:`BenchmarkAdapter` knows three things about a benchmark:

1. How to find and parse trajectory artifacts on disk into the
   canonical :class:`~trajaudit.core.trajectory.Trajectory` schema.
2. How to classify workspace paths so Layer 1's filesystem diff can
   tell source from tests from harness internals.
3. What container image / runtime to use when Layer 1 replays a
   trajectory.

Adapters are registered by ``benchmark_id``; the runner looks them up
by the id passed on the CLI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from trajaudit.core.trajectory import Trajectory
from trajaudit.layer1_workspace.fs_differ import PathClass


class BenchmarkAdapter(ABC):
    """Common contract for benchmark adapters."""

    #: Stable benchmark identifier (e.g. ``"swe-bench-verified"``).
    benchmark_id: str

    @abstractmethod
    def discover(self, root: Path) -> list[Path]:
        """Return every trajectory directory under ``root``."""

    @abstractmethod
    def load(self, trajectory_path: Path) -> Trajectory:
        """Parse one trajectory directory into the canonical schema."""

    @abstractmethod
    def classify_path(self, path: Path) -> PathClass:
        """Classify a workspace-relative path for Layer 1's diff."""

    @abstractmethod
    def replay_image(self, task_id: str) -> str:
        """Return the container image to use when replaying ``task_id``."""


_REGISTRY: dict[str, type[BenchmarkAdapter]] = {}


def register(cls: type[BenchmarkAdapter]) -> type[BenchmarkAdapter]:
    """Decorator: register a benchmark adapter class by its ``benchmark_id``."""
    _REGISTRY[cls.benchmark_id] = cls
    return cls


def get_adapter(benchmark_id: str) -> BenchmarkAdapter:
    """Look up and instantiate the adapter for ``benchmark_id``."""
    raise NotImplementedError("Phase 1: implement adapter registry lookup.")
