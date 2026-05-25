"""Tests for the unified Trajectory event stream and its discriminated union."""

from __future__ import annotations

from trajaudit.core.events import (
    ObservationEvent,
    ReasoningEvent,
    ScoringEvent,
    ToolCallEvent,
)
from trajaudit.core.trajectory import Trajectory


def _sample_trajectory() -> Trajectory:
    return Trajectory(
        trajectory_id="t-1",
        benchmark="dummy-bench",
        task_id="task-001",
        agent_id="agent-x",
        events=[
            ReasoningEvent(content="I will run pytest."),
            ToolCallEvent(
                tool_name="shell",
                arguments={"cmd": "pytest -q"},
                call_id="c-1",
            ),
            ObservationEvent(content="1 passed", source="stdout", call_id="c-1"),
            ReasoningEvent(content="Now I will edit the file."),
            ToolCallEvent(
                tool_name="edit_file",
                arguments={"path": "src/foo.py"},
                call_id="c-2",
            ),
            ScoringEvent(score=1.0, passed=True, details={"by": "harness"}),
        ],
    )


def test_round_trip_serialization_all_variants() -> None:
    traj = _sample_trajectory()
    restored = Trajectory.model_validate_json(traj.model_dump_json())
    assert restored == traj


def test_discriminator_resolves_each_variant() -> None:
    traj = _sample_trajectory()
    restored = Trajectory.model_validate_json(traj.model_dump_json())
    assert [type(e) for e in restored.events] == [
        ReasoningEvent,
        ToolCallEvent,
        ObservationEvent,
        ReasoningEvent,
        ToolCallEvent,
        ScoringEvent,
    ]


def test_paired_calls_matches_by_call_id() -> None:
    traj = _sample_trajectory()
    pairs = list(traj.paired_calls())
    assert len(pairs) == 2
    call_1, obs_1 = pairs[0]
    assert call_1.call_id == "c-1"
    assert obs_1 is not None
    assert obs_1.call_id == "c-1"
    assert obs_1.content == "1 passed"
    call_2, obs_2 = pairs[1]
    assert call_2.call_id == "c-2"
    assert obs_2 is None


def test_paired_calls_none_call_id_unmatched() -> None:
    traj = Trajectory(
        trajectory_id="t-2",
        benchmark="dummy",
        task_id="task-2",
        events=[
            ToolCallEvent(tool_name="shell", arguments={}, call_id=None),
            ObservationEvent(content="output", source="stdout", call_id=None),
        ],
    )
    pairs = list(traj.paired_calls())
    assert len(pairs) == 1
    call, obs = pairs[0]
    assert call.call_id is None
    assert obs is None


def test_filter_iterators() -> None:
    traj = _sample_trajectory()
    assert sum(1 for _ in traj.reasoning()) == 2
    assert sum(1 for _ in traj.tool_calls()) == 2
    assert sum(1 for _ in traj.observations()) == 1


def test_ordering_preserved_through_round_trip() -> None:
    traj = _sample_trajectory()
    restored = Trajectory.model_validate_json(traj.model_dump_json())
    original_types = [type(e).__name__ for e in traj.events]
    restored_types = [type(e).__name__ for e in restored.events]
    assert original_types == restored_types
