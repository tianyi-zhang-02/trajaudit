"""Benchmark-agnostic data model for agent trajectories.

A :class:`Trajectory` captures everything TrajAudit needs to audit a
single agent run on a single benchmark task: the task identifier, the
sequence of :class:`Step` objects the agent emitted, the file edits it
produced, the shell commands it executed, and the harness's reported
pass/fail verdict.

Benchmark-specific adapters (see :mod:`trajaudit.benchmarks`) parse the
raw artifacts of a given benchmark into this shared schema; downstream
layers only ever see the schema, never the benchmark-native format.

Phase 1 will decide whether to subclass an existing standard
(OpenInference traces, Inspect AI eval logs, AgentOps) or to ship a
fresh schema; the field names below are conservative and easy to
re-map either way.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StepType(StrEnum):
    """Coarse classification of an agent step."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL = "shell"
    TOOL_CALL = "tool_call"
    THOUGHT = "thought"
    OTHER = "other"


class FileEdit(BaseModel):
    """A single file-level mutation performed by the agent."""

    path: Path = Field(..., description="Path to the file (workspace-relative when possible).")
    before: str | None = Field(None, description="File contents prior to the edit, when known.")
    after: str | None = Field(None, description="File contents after the edit, when known.")
    created: bool = Field(False, description="True if this edit created a new file.")
    deleted: bool = Field(False, description="True if this edit deleted the file.")


class ShellCommand(BaseModel):
    """A shell command observed in the trajectory."""

    command: str = Field(..., description="The literal command line, as issued.")
    cwd: Path | None = Field(None, description="Working directory at invocation, if known.")
    exit_code: int | None = Field(None, description="Process exit code, if captured.")
    stdout: str | None = Field(None, description="Captured stdout, if any.")
    stderr: str | None = Field(None, description="Captured stderr, if any.")


class Step(BaseModel):
    """A single step in an agent trajectory."""

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

    steps: list[Step] = Field(default_factory=list)
    file_edits: list[FileEdit] = Field(default_factory=list)
    shell_commands: list[ShellCommand] = Field(default_factory=list)
    harness_result: HarnessResult | None = None

    workspace_root: Path | None = Field(
        None, description="Local path to the workspace snapshot, if available."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dir(cls, path: Path) -> Trajectory:
        """Load a trajectory from a directory of artifacts.

        Each benchmark adapter is responsible for the exact on-disk
        layout; this classmethod dispatches to the right adapter based
        on a manifest file at ``path / 'trajaudit.json'``.
        """
        raise NotImplementedError("Phase 1: dispatch to benchmark adapter from manifest.")
