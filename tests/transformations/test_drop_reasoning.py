"""Tests for ``drop_reasoning``."""

from __future__ import annotations

from monitorstress.core.events import (
    ObservationEvent,
    ReasoningEvent,
    ScoringEvent,
    ToolCallEvent,
)
from monitorstress.core.trajectory import Trajectory
from monitorstress.transformations import drop_reasoning


def test_happy_path_drops_only_reasoning(sample_trajectory: Trajectory) -> None:
    result = drop_reasoning(sample_trajectory)
    assert len(result.events) == len(sample_trajectory.events) - 3  # 3 reasoning events removed
    assert all(not isinstance(e, ReasoningEvent) for e in result.events)
    # Order preserved among surviving event types.
    types = [type(e).__name__ for e in result.events]
    assert types == [
        "ToolCallEvent", "ObservationEvent",
        "ToolCallEvent", "ObservationEvent",
        "ToolCallEvent", "ObservationEvent",
        "ScoringEvent",
    ]


def test_transformations_applied_metadata(sample_trajectory: Trajectory) -> None:
    result = drop_reasoning(sample_trajectory)
    assert result.metadata["transformations_applied"] == ["drop_reasoning"]
    # Pre-existing metadata preserved.
    assert result.metadata["pre_existing_flag"] == "keep_me"
    assert result.metadata["labels"] == ["normal"]


def test_input_not_mutated(sample_trajectory: Trajectory) -> None:
    original_event_count = len(sample_trajectory.events)
    original_metadata = dict(sample_trajectory.metadata)
    drop_reasoning(sample_trajectory)
    assert len(sample_trajectory.events) == original_event_count
    assert sample_trajectory.metadata == original_metadata
    assert "transformations_applied" not in sample_trajectory.metadata


def test_no_reasoning_events_still_records_provenance() -> None:
    traj = Trajectory(
        trajectory_id="t-1",
        benchmark="test",
        task_id="task-1",
        events=[
            ToolCallEvent(tool_name="bash", arguments={}, call_id="c-1"),
            ObservationEvent(content="ok", call_id="c-1"),
        ],
    )
    result = drop_reasoning(traj)
    assert len(result.events) == 2  # nothing to remove
    assert result.metadata["transformations_applied"] == ["drop_reasoning"]


def test_empty_trajectory(empty_trajectory: Trajectory) -> None:
    result = drop_reasoning(empty_trajectory)
    assert result.events == []
    assert result.metadata["transformations_applied"] == ["drop_reasoning"]


def test_chained_transformations_extend_provenance(sample_trajectory: Trajectory) -> None:
    once = drop_reasoning(sample_trajectory)
    twice = drop_reasoning(once)
    assert twice.metadata["transformations_applied"] == ["drop_reasoning", "drop_reasoning"]


def test_scoring_event_preserved(sample_trajectory: Trajectory) -> None:
    result = drop_reasoning(sample_trajectory)
    scoring_events = [e for e in result.events if isinstance(e, ScoringEvent)]
    assert len(scoring_events) == 1
