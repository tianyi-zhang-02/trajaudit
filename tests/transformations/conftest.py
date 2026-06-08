"""Shared trajectory builders for the transformation test files."""

from __future__ import annotations

import pytest

from monitorstress.core.events import (
    ObservationEvent,
    ReasoningEvent,
    ScoringEvent,
    ToolCallEvent,
)
from monitorstress.core.trajectory import Trajectory


@pytest.fixture
def sample_trajectory() -> Trajectory:
    """A 10-event trajectory with all four event variants and call-id pairs."""
    return Trajectory(
        trajectory_id="t-sample",
        benchmark="test",
        task_id="task-1",
        events=[
            ReasoningEvent(content="I will check the directory."),
            ToolCallEvent(tool_name="bash", arguments={"cmd": "ls"}, call_id="c-1"),
            ObservationEvent(content="a.py b.py", source="stdout", call_id="c-1"),
            ReasoningEvent(content="Now let me edit a.py."),
            ToolCallEvent(tool_name="edit", arguments={"path": "a.py"}, call_id="c-2"),
            ObservationEvent(content="file written", source="tool_result", call_id="c-2"),
            ReasoningEvent(content="Run the tests."),
            ToolCallEvent(tool_name="bash", arguments={"cmd": "pytest"}, call_id="c-3"),
            ObservationEvent(content="1 passed", source="stdout", call_id="c-3"),
            ScoringEvent(score=1.0, passed=True),
        ],
        metadata={"labels": ["normal"], "pre_existing_flag": "keep_me"},
    )


@pytest.fixture
def empty_trajectory() -> Trajectory:
    return Trajectory(
        trajectory_id="t-empty",
        benchmark="test",
        task_id="task-1",
    )


@pytest.fixture
def single_event_trajectory() -> Trajectory:
    return Trajectory(
        trajectory_id="t-single",
        benchmark="test",
        task_id="task-1",
        events=[ReasoningEvent(content="only event")],
    )


@pytest.fixture
def short_trajectory_4_events() -> Trajectory:
    """A 4-event trajectory — under the truncate_observations threshold."""
    return Trajectory(
        trajectory_id="t-short",
        benchmark="test",
        task_id="task-1",
        events=[
            ReasoningEvent(content="r1"),
            ToolCallEvent(tool_name="bash", arguments={}, call_id="c-1"),
            ObservationEvent(content="o1", call_id="c-1"),
            ScoringEvent(score=1.0, passed=True),
        ],
    )
