"""Terminal-Bench adapter.

Parses Terminal-Bench trajectories — typically tmux/asciinema-style
session recordings plus per-task grader output — into the canonical
:class:`~trajaudit.core.trajectory.Trajectory` schema.

Terminal-Bench's filesystem layout is different from SWE-bench's:
most tasks operate on scratch directories under ``/tmp`` or the
user's home, and the grader script lives outside the agent's writable
workspace. The classifier reflects that.
"""

from __future__ import annotations

from pathlib import Path

from trajaudit.benchmarks.base import BenchmarkAdapter, register
from trajaudit.core.trajectory import Trajectory
from trajaudit.layer1_workspace.fs_differ import PathClass


@register
class TerminalBenchAdapter(BenchmarkAdapter):
    """Adapter for Terminal-Bench."""

    benchmark_id = "terminal-bench"

    def discover(self, root: Path) -> list[Path]:
        raise NotImplementedError("Phase 6: scan Terminal-Bench run directory.")

    def load(self, trajectory_path: Path) -> Trajectory:
        raise NotImplementedError("Phase 6: parse Terminal-Bench artifacts.")

    def classify_path(self, path: Path) -> PathClass:
        raise NotImplementedError("Phase 6: implement Terminal-Bench path classifier.")

    def replay_image(self, task_id: str) -> str:
        raise NotImplementedError("Phase 6: map task_id to per-task replay image.")
