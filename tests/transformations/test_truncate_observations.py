"""Tests for ``truncate_observations``."""

from __future__ import annotations

import pytest

from trajaudit.core.trajectory import Trajectory
from trajaudit.transformations import truncate_observations


def test_happy_path_default_fraction_removes_20pct(sample_trajectory: Trajectory) -> None:
    # 10 events × 0.2 = 2 events removed → 8 remain.
    result = truncate_observations(sample_trajectory)
    assert len(result.events) == 8
    # Same prefix.
    assert result.events == sample_trajectory.events[:8]


def test_fraction_is_configurable(sample_trajectory: Trajectory) -> None:
    # 10 events × 0.5 = 5 removed → 5 remain.
    result = truncate_observations(sample_trajectory, fraction=0.5)
    assert len(result.events) == 5


def test_fraction_zero_is_noop(sample_trajectory: Trajectory) -> None:
    result = truncate_observations(sample_trajectory, fraction=0.0)
    assert len(result.events) == len(sample_trajectory.events)
    assert result.metadata["transformations_applied"] == ["truncate_observations"]


def test_fraction_one_truncates_everything(sample_trajectory: Trajectory) -> None:
    result = truncate_observations(sample_trajectory, fraction=1.0)
    assert result.events == []


def test_short_trajectory_under_threshold(short_trajectory_4_events: Trajectory) -> None:
    """< 5 events: keep all events but still record the transformation."""
    result = truncate_observations(short_trajectory_4_events)
    assert len(result.events) == 4  # unchanged
    assert result.metadata["transformations_applied"] == ["truncate_observations"]


def test_empty_trajectory(empty_trajectory: Trajectory) -> None:
    result = truncate_observations(empty_trajectory)
    assert result.events == []
    assert result.metadata["transformations_applied"] == ["truncate_observations"]


def test_fraction_out_of_range_raises(sample_trajectory: Trajectory) -> None:
    with pytest.raises(ValueError, match="fraction must be"):
        truncate_observations(sample_trajectory, fraction=1.5)
    with pytest.raises(ValueError, match="fraction must be"):
        truncate_observations(sample_trajectory, fraction=-0.1)


def test_input_not_mutated(sample_trajectory: Trajectory) -> None:
    original_count = len(sample_trajectory.events)
    truncate_observations(sample_trajectory, fraction=0.5)
    assert len(sample_trajectory.events) == original_count


def test_rounding_to_nearest_integer() -> None:
    # 11 events × 0.2 = 2.2 → rounds to 2.
    events = [
        type(e)(**e.model_dump()) for e in [
            __import__("trajaudit.core.events", fromlist=["ReasoningEvent"]).ReasoningEvent(content=f"r{i}")
            for i in range(11)
        ]
    ]
    traj = Trajectory(trajectory_id="t", benchmark="test", task_id="t", events=events)
    result = truncate_observations(traj, fraction=0.2)
    assert len(result.events) == 11 - 2
