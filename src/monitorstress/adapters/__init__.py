"""Corpus adapters that convert external datasets into :class:`Trajectory` objects.

Each adapter is responsible for parsing one external data format and emitting
:class:`~monitorstress.core.trajectory.Trajectory` instances populated with the
appropriate :data:`~monitorstress.core.events.TrajectoryEvent` variants.

v0.1 ships one adapter (MALT). The pattern is intentionally small: a top-level
``load_*`` generator plus a row-level conversion helper used in tests.
"""

from __future__ import annotations

from monitorstress.adapters.malt import load_malt_split, malt_row_to_trajectory

__all__ = ["load_malt_split", "malt_row_to_trajectory"]
