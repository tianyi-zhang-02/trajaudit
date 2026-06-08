"""Structural transformations on :class:`Trajectory` event streams.

Each transformation is a pure function ``Trajectory -> Trajectory`` that
returns a new object. The original trajectory is never mutated, so the same
Trajectory can be fed through multiple transformations for side-by-side
comparison runs.

Every transformation appends its name to ``trajectory.metadata['transformations_applied']``
(a ``list[str]``), so chained transformations remain inspectable.

v0.1 ships three transformations; semantic transformations land in v0.2.
"""

from __future__ import annotations

from monitorstress.transformations.structural import (
    apply_structural_battery,
    drop_reasoning,
    pad_with_noops,
    truncate_observations,
)

__all__ = [
    "apply_structural_battery",
    "drop_reasoning",
    "pad_with_noops",
    "truncate_observations",
]
