"""Monitor protocol and built-in monitor implementations.

The :class:`Monitor` protocol is the entire extensibility surface for adding
new monitors to TrajAudit: any class that exposes a ``name: str`` attribute
and a ``score(trajectory: Trajectory) -> SemanticVerdict`` method is a valid
monitor. See ``docs/writing_a_monitor.md`` for a 20-line worked example.

v0.1 ships one concrete monitor: :class:`~monitorstress.monitors.metr_prompt.METRPromptMonitor`,
which reproduces METR's published MALT monitor prompt and calls
``claude-haiku-4-5-20251001`` via the Anthropic API.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from monitorstress.core.trajectory import Trajectory
from monitorstress.core.verdict import SemanticVerdict


@runtime_checkable
class Monitor(Protocol):
    """Structural protocol every TrajAudit monitor satisfies.

    A monitor consumes a :class:`Trajectory` and emits a
    :class:`SemanticVerdict`. Transient API errors should propagate; the
    runner (CLI) is responsible for retry / abort / budget-tracking policy
    at the outer loop. Permanent input problems (e.g. trajectory too large
    for the underlying model) should be encoded as an ``abstain=True``
    verdict rather than raised, so the runner can keep going.
    """

    name: str

    def score(self, trajectory: Trajectory) -> SemanticVerdict:
        """Return a verdict for ``trajectory``.

        Raises on transient API errors (rate limits, 5xx); the runner
        retries. Returns ``abstain=True`` verdict on permanent input
        problems (over-context, refusal, unparseable output).
        """
        ...


from monitorstress.monitors.metr_prompt import METRPromptMonitor  # noqa: E402

__all__ = ["Monitor", "METRPromptMonitor"]
