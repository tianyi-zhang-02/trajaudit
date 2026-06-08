"""Three structural transformations on Trajectory event streams.

Each function is a *pure* ``Trajectory -> Trajectory`` mapping that never
mutates its input. Pydantic's :meth:`BaseModel.model_copy` is the underlying
primitive — events get replaced with a freshly-built list, and metadata is
replaced with a freshly-built dict that includes a ``transformations_applied``
provenance trail.

Why structural-only for v0.1
============================
The pivot decision (see ``docs/pivot_decision.md``) framed the v1 contribution
as a *stress-test runner* that measures how monitor performance degrades
under transcript transformations. v0.1 ships three transformations that are
cheap, deterministic, and don't require an LLM — they probe whether the
monitor's signal is robust to coarse structural manipulation. v0.2 adds
semantic transformations (CoT vague-ification, summarization) that do
require an LLM.
"""

from __future__ import annotations

from typing import Any

from monitorstress.core.events import (
    ObservationEvent,
    ReasoningEvent,
    ToolCallEvent,
    TrajectoryEvent,
)
from monitorstress.core.trajectory import Trajectory


def _with_transform(
    original: Trajectory,
    new_events: list[TrajectoryEvent],
    transform_name: str,
) -> Trajectory:
    """Build a new Trajectory from ``original`` with replaced events and a
    provenance entry appended to ``metadata['transformations_applied']``.

    The original trajectory is never mutated: the events list and metadata
    dict on the returned Trajectory are fresh objects.
    """
    new_metadata: dict[str, Any] = dict(original.metadata)
    applied: list[str] = list(new_metadata.get("transformations_applied", []))
    applied.append(transform_name)
    new_metadata["transformations_applied"] = applied
    return original.model_copy(
        update={"events": new_events, "metadata": new_metadata}
    )


def drop_reasoning(trajectory: Trajectory) -> Trajectory:
    """Return a new Trajectory with all :class:`ReasoningEvent`\\ s removed.

    All other events (tool calls, observations, scoring) keep their original
    order. The Trajectory's metadata is augmented with
    ``transformations_applied += ['drop_reasoning']``.

    No edge cases: a Trajectory with zero reasoning events is returned with
    the same event list and the provenance entry still appended (the
    transformation was applied, the input simply had nothing to remove).
    """
    new_events: list[TrajectoryEvent] = [
        e for e in trajectory.events if not isinstance(e, ReasoningEvent)
    ]
    return _with_transform(trajectory, new_events, "drop_reasoning")


def truncate_observations(trajectory: Trajectory, fraction: float = 0.2) -> Trajectory:
    """Return a new Trajectory with the final ``fraction`` of events removed.

    Despite the name, the truncation operates on the unified event stream —
    not specifically on :class:`ObservationEvent`\\ s. The name reflects the
    typical effect: the *end* of an agent trajectory is dominated by
    observations and a final scoring event, so trimming the tail mostly
    drops those.

    Rounded to the nearest integer (e.g., 11 events × 0.2 = 2.2 → 2 removed).

    **Edge case (documented):** trajectories with fewer than 5 events are
    returned with their full event list — no truncation — but the
    transformation is still recorded in ``transformations_applied`` so
    downstream code knows the function was called. This avoids degenerate
    cases where rounding leaves a single-event trajectory.
    """
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"fraction must be in [0.0, 1.0]; got {fraction!r}")

    n = len(trajectory.events)
    if n < 5:
        return _with_transform(trajectory, list(trajectory.events), "truncate_observations")

    to_remove = round(n * fraction)
    new_events = list(trajectory.events[: n - to_remove])
    return _with_transform(trajectory, new_events, "truncate_observations")


def pad_with_noops(
    trajectory: Trajectory,
    noop_tool: str = "ls",
    insertion_rate: float = 0.5,
) -> Trajectory:
    """Return a new Trajectory with deterministic noop tool-call pairs inserted.

    ``insertion_rate`` controls density: ``0.5`` inserts a noop pair after
    every 2nd existing event, ``1.0`` after every event, ``0.25`` after every
    4th event. The insertion gap is computed as ``k = max(1, round(1 /
    insertion_rate))`` and a noop pair is inserted after event indices
    ``k-1, 2k-1, 3k-1, ...`` (zero-based), never after the final event. The
    pattern is fully deterministic — no randomness — so consecutive runs
    against the same monitor are bit-identical.

    Each noop is a (:class:`ToolCallEvent`, :class:`ObservationEvent`) pair
    sharing a synthetic ``call_id`` of the form ``noop-{event_index}``.
    The tool call has empty arguments; the observation returns a fixed
    plausible directory listing (``"file1.py file2.py README.md"``). Both
    carry ``metadata={"noop": True}`` so downstream filters can drop them
    cleanly.

    **Edge cases:** empty trajectory or single-event trajectory → no
    insertion (no gaps to fill), but the transformation is still recorded
    in ``transformations_applied``. ``insertion_rate <= 0`` → no insertion
    (same handling).
    """
    if not 0.0 <= insertion_rate <= 1.0:
        raise ValueError(
            f"insertion_rate must be in [0.0, 1.0]; got {insertion_rate!r}"
        )

    events = list(trajectory.events)
    if len(events) <= 1 or insertion_rate == 0.0:
        return _with_transform(trajectory, events, "pad_with_noops")

    k = max(1, round(1 / insertion_rate))
    NOOP_OUTPUT = "file1.py file2.py README.md"

    new_events: list[TrajectoryEvent] = []
    for i, ev in enumerate(events):
        new_events.append(ev)
        # Skip insertion after the very last event.
        if i == len(events) - 1:
            continue
        if (i + 1) % k == 0:
            noop_id = f"noop-{i + 1}"
            new_events.append(
                ToolCallEvent(
                    tool_name=noop_tool,
                    arguments={},
                    call_id=noop_id,
                    metadata={"noop": True},
                )
            )
            new_events.append(
                ObservationEvent(
                    content=NOOP_OUTPUT,
                    source="tool_result",
                    call_id=noop_id,
                    metadata={"noop": True},
                )
            )

    return _with_transform(trajectory, new_events, "pad_with_noops")


def apply_structural_battery(trajectory: Trajectory) -> dict[str, Trajectory]:
    """Apply all three structural transformations and return a dict of variants.

    The returned dict has keys ``"clean"``, ``"drop_reasoning"``,
    ``"truncate_obs"``, ``"pad_noops"``. ``"clean"`` is the original
    trajectory; the other three are each independently produced from the
    original. The CLI iterates over this dict to feed each variant through
    the monitor.

    Note the key ``"truncate_obs"`` (not ``"truncate_observations"``) and
    ``"pad_noops"`` (not ``"pad_with_noops"``) — short keys keep the report
    card table narrow.
    """
    return {
        "clean": trajectory,
        "drop_reasoning": drop_reasoning(trajectory),
        "truncate_obs": truncate_observations(trajectory),
        "pad_noops": pad_with_noops(trajectory),
    }
