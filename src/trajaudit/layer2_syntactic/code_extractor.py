"""Extract code edits from a trajectory for AST analysis.

Trajectories carry file edits in a benchmark-agnostic form (see
:class:`trajaudit.core.trajectory.FileEdit`). This module filters
those down to the edits worth AST-scanning — Python files only,
ignoring deletions, and so on — and surfaces them as
:class:`CodeEdit` pairs that the scanner can consume directly.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from trajaudit.core.trajectory import Trajectory


class CodeEdit(BaseModel):
    """A single code-level edit ready for AST analysis."""

    path: Path
    before_source: str | None = None
    after_source: str
    language: str = "python"


def extract_code_from_trajectory(trajectory: Trajectory) -> list[CodeEdit]:
    """Return every Python edit in the trajectory, filtered and normalized."""
    raise NotImplementedError("Phase 2: implement Python-edit extraction.")
