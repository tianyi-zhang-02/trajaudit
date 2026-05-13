"""SWE-bench Verified adapter.

Parses SWE-bench Verified trajectories — typically per-task directories
containing the model patch, the test patch, the agent's action log,
and the harness's ``report.json`` — into the canonical
:class:`~trajaudit.core.trajectory.Trajectory` schema.

Path classification is tuned for the SWE-bench convention of placing
bug-fix tests under ``tests/`` (or repo-specific test trees), the
system under test under the project root, and the harness's own
artifacts under ``.swebench/``.
"""

from __future__ import annotations

from pathlib import Path

from trajaudit.benchmarks.base import BenchmarkAdapter, register
from trajaudit.core.trajectory import Trajectory
from trajaudit.layer1_workspace.fs_differ import PathClass


@register
class SWEBenchAdapter(BenchmarkAdapter):
    """Adapter for SWE-bench Verified."""

    benchmark_id = "swe-bench-verified"

    def discover(self, root: Path) -> list[Path]:
        raise NotImplementedError("Phase 1: scan SWE-bench run directory.")

    def load(self, trajectory_path: Path) -> Trajectory:
        raise NotImplementedError("Phase 1: parse SWE-bench artifacts.")

    def classify_path(self, path: Path) -> PathClass:
        raise NotImplementedError("Phase 1: implement SWE-bench path classifier.")

    def replay_image(self, task_id: str) -> str:
        raise NotImplementedError("Phase 3: map task_id to per-repo replay image.")
