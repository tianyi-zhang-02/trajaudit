"""Tests for ``pad_with_noops``."""

from __future__ import annotations

import pytest

from monitorstress.core.events import ObservationEvent, ToolCallEvent
from monitorstress.core.trajectory import Trajectory
from monitorstress.transformations import pad_with_noops


def test_happy_path_default_rate(sample_trajectory: Trajectory) -> None:
    # 10 events, insertion_rate=0.5 → k=2, insert after every 2nd event,
    # never after the last (event 9). Inserts after indices 1, 3, 5, 7 →
    # 4 insertions × 2 events each = 8 new events. Total = 10 + 8 = 18.
    result = pad_with_noops(sample_trajectory)
    assert len(result.events) == 18


def test_insertion_rate_one_inserts_at_every_gap(sample_trajectory: Trajectory) -> None:
    # k=1, insert after every event except the last → 9 insertions × 2 = 18 new.
    result = pad_with_noops(sample_trajectory, insertion_rate=1.0)
    assert len(result.events) == 10 + 18


def test_insertion_rate_zero_inserts_nothing(sample_trajectory: Trajectory) -> None:
    result = pad_with_noops(sample_trajectory, insertion_rate=0.0)
    assert len(result.events) == 10
    assert result.metadata["transformations_applied"] == ["pad_with_noops"]


def test_inserted_noops_have_matching_call_ids(sample_trajectory: Trajectory) -> None:
    result = pad_with_noops(sample_trajectory)
    noop_calls = [
        e for e in result.events
        if isinstance(e, ToolCallEvent) and e.metadata.get("noop") is True
    ]
    noop_obs = [
        e for e in result.events
        if isinstance(e, ObservationEvent) and e.metadata.get("noop") is True
    ]
    assert len(noop_calls) == len(noop_obs)
    # Each call has a paired observation by call_id.
    call_ids = {c.call_id for c in noop_calls}
    obs_ids = {o.call_id for o in noop_obs}
    assert call_ids == obs_ids


def test_noop_tool_name_is_configurable(sample_trajectory: Trajectory) -> None:
    result = pad_with_noops(sample_trajectory, noop_tool="pwd")
    noop_calls = [
        e for e in result.events
        if isinstance(e, ToolCallEvent) and e.metadata.get("noop") is True
    ]
    assert all(c.tool_name == "pwd" for c in noop_calls)


def test_deterministic_pattern(sample_trajectory: Trajectory) -> None:
    # Two calls produce bit-identical output.
    a = pad_with_noops(sample_trajectory)
    b = pad_with_noops(sample_trajectory)
    assert a == b


def test_empty_trajectory(empty_trajectory: Trajectory) -> None:
    result = pad_with_noops(empty_trajectory)
    assert result.events == []
    assert result.metadata["transformations_applied"] == ["pad_with_noops"]


def test_single_event_trajectory(single_event_trajectory: Trajectory) -> None:
    """No gaps → no insertions, but transformation still recorded."""
    result = pad_with_noops(single_event_trajectory)
    assert len(result.events) == 1
    assert result.metadata["transformations_applied"] == ["pad_with_noops"]


def test_insertion_rate_out_of_range_raises(sample_trajectory: Trajectory) -> None:
    with pytest.raises(ValueError, match="insertion_rate must be"):
        pad_with_noops(sample_trajectory, insertion_rate=1.5)
    with pytest.raises(ValueError, match="insertion_rate must be"):
        pad_with_noops(sample_trajectory, insertion_rate=-0.1)


def test_input_not_mutated(sample_trajectory: Trajectory) -> None:
    original_count = len(sample_trajectory.events)
    pad_with_noops(sample_trajectory)
    assert len(sample_trajectory.events) == original_count


def test_apply_structural_battery_returns_four_variants(
    sample_trajectory: Trajectory,
) -> None:
    from monitorstress.transformations import apply_structural_battery

    variants = apply_structural_battery(sample_trajectory)
    assert set(variants) == {"clean", "drop_reasoning", "truncate_obs", "pad_noops"}
    # 'clean' is the original (same identity).
    assert variants["clean"] is sample_trajectory
    # Each transformed variant differs from clean.
    for key in ("drop_reasoning", "truncate_obs", "pad_noops"):
        assert variants[key] is not sample_trajectory
        assert variants[key].events != sample_trajectory.events or \
               variants[key].metadata != sample_trajectory.metadata
