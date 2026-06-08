"""Benchmark-agnostic data model for agent trajectories.

A :class:`Trajectory` captures everything TrajAudit needs to audit a
single agent run on a single benchmark task: the task identifier, the
ordered stream of typed events the agent and harness emitted, and the
harness's reported pass/fail outcome.

Events are a discriminated union of
:class:`~monitorstress.core.events.ReasoningEvent`,
:class:`~monitorstress.core.events.ToolCallEvent`,
:class:`~monitorstress.core.events.ObservationEvent`, and
:class:`~monitorstress.core.events.ScoringEvent`. The unified ordered list
preserves the interleaving between reasoning and tool calls — which is
what every realistic monitor (METR, EvilGenie, Meerkat, MALT) operates
on.

Benchmark-specific adapters (see :mod:`monitorstress.benchmarks`) parse the
raw artifacts of a given benchmark into this shared schema; downstream
layers only ever see the schema, never the benchmark-native format.

The legacy :class:`StepType`, :class:`Step`, :class:`FileEdit`, and
:class:`ShellCommand` types remain importable for one release cycle to
ease migration. They are no longer referenced from :class:`Trajectory`
and new code must not use them.

Phase 1 will decide whether to subclass an existing standard
(OpenInference traces, Inspect AI eval logs, AgentOps) or to ship a
fresh schema; the field names below are conservative and easy to
re-map either way.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from monitorstress.core.events import (
    ObservationEvent,
    ReasoningEvent,
    ToolCallEvent,
    TrajectoryEvent,
)


class StepType(StrEnum):
    """Coarse classification of a legacy agent step.

    .. deprecated::
       Use the :data:`~monitorstress.core.events.TrajectoryEvent` variants
       (:class:`~monitorstress.core.events.ReasoningEvent`,
       :class:`~monitorstress.core.events.ToolCallEvent`,
       :class:`~monitorstress.core.events.ObservationEvent`,
       :class:`~monitorstress.core.events.ScoringEvent`). Retained for one
       release cycle to ease migration.
    """

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL = "shell"
    TOOL_CALL = "tool_call"
    THOUGHT = "thought"
    OTHER = "other"


class FileEdit(BaseModel):
    """A single file-level mutation performed by the agent.

    .. deprecated::
       Encode as a :class:`~monitorstress.core.events.ToolCallEvent` (the
       edit invocation) followed by a
       :class:`~monitorstress.core.events.ObservationEvent` carrying the
       resulting diff. Retained for one release cycle.
    """

    path: Path = Field(..., description="Path to the file (workspace-relative when possible).")
    before: str | None = Field(None, description="File contents prior to the edit, when known.")
    after: str | None = Field(None, description="File contents after the edit, when known.")
    created: bool = Field(False, description="True if this edit created a new file.")
    deleted: bool = Field(False, description="True if this edit deleted the file.")


class ShellCommand(BaseModel):
    """A shell command observed in the trajectory.

    .. deprecated::
       Encode as a :class:`~monitorstress.core.events.ToolCallEvent`
       (``tool_name="shell"``) followed by a
       :class:`~monitorstress.core.events.ObservationEvent` carrying
       stdout/stderr. Retained for one release cycle.
    """

    command: str = Field(..., description="The literal command line, as issued.")
    cwd: Path | None = Field(None, description="Working directory at invocation, if known.")
    exit_code: int | None = Field(None, description="Process exit code, if captured.")
    stdout: str | None = Field(None, description="Captured stdout, if any.")
    stderr: str | None = Field(None, description="Captured stderr, if any.")


class Step(BaseModel):
    """A single step in a legacy agent trajectory.

    .. deprecated::
       Use the :data:`~monitorstress.core.events.TrajectoryEvent` variants.
       :attr:`Trajectory.events` replaces the old
       ``steps`` / ``file_edits`` / ``shell_commands`` triple.
    """

    index: int = Field(..., description="Zero-based index in the trajectory.")
    type: StepType
    timestamp: datetime | None = None
    content: str = Field(..., description="Free-form textual content of the step.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class HarnessResult(BaseModel):
    """The benchmark harness's reported outcome for the task."""

    passed: bool = Field(..., description="The harness's binary pass/fail verdict.")
    score: float | None = Field(None, description="Optional numeric score, if applicable.")
    raw: dict[str, Any] = Field(
        default_factory=dict, description="Benchmark-specific raw result payload."
    )


class Trajectory(BaseModel):
    """A single agent run on a single benchmark task."""

    trajectory_id: str = Field(..., description="Globally unique id for this trajectory.")
    benchmark: str = Field(..., description="Benchmark id, e.g. 'swe-bench-verified'.")
    task_id: str = Field(..., description="Task id within the benchmark.")
    agent_id: str | None = Field(
        None, description="Identifier for the agent/model that produced the run."
    )

    events: list[TrajectoryEvent] = Field(
        default_factory=list,
        description="Ordered, interleaved stream of reasoning, tool calls, observations, scoring.",
    )
    harness_result: HarnessResult | None = None

    workspace_root: Path | None = Field(
        None, description="Local path to the workspace snapshot, if available."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def tool_calls(self) -> Iterator[ToolCallEvent]:
        """Yield every :class:`ToolCallEvent` in order."""
        return (e for e in self.events if isinstance(e, ToolCallEvent))

    def observations(self) -> Iterator[ObservationEvent]:
        """Yield every :class:`ObservationEvent` in order."""
        return (e for e in self.events if isinstance(e, ObservationEvent))

    def reasoning(self) -> Iterator[ReasoningEvent]:
        """Yield every :class:`ReasoningEvent` in order."""
        return (e for e in self.events if isinstance(e, ReasoningEvent))

    def paired_calls(
        self,
    ) -> Iterator[tuple[ToolCallEvent, ObservationEvent | None]]:
        """Yield ``(ToolCallEvent, ObservationEvent | None)`` pairs.

        Pairing is by ``call_id``. If a tool call has no ``call_id``,
        or no observation in the trajectory shares the same ``call_id``,
        the second element is ``None``. The first observation matching
        a given ``call_id`` wins, so repeated ids are handled
        deterministically.
        """
        obs_by_id: dict[str, ObservationEvent] = {}
        for obs in self.observations():
            if obs.call_id is not None:
                obs_by_id.setdefault(obs.call_id, obs)
        for call in self.tool_calls():
            match = obs_by_id.get(call.call_id) if call.call_id is not None else None
            yield (call, match)

    @classmethod
    def from_dir(cls, path: Path) -> Trajectory:
        """Load a trajectory from a directory of artifacts.

        Each benchmark adapter is responsible for the exact on-disk
        layout; this classmethod dispatches to the right adapter based
        on a manifest file at ``path / 'monitorstress.json'``.
        """
        raise NotImplementedError("Phase 1: dispatch to benchmark adapter from manifest.")
