"""Subprocess tracing for Layer 1.

The :class:`ProcessTracer` ingests the agent's shell-command log and,
for the in-sandbox replay, captures the actual processes spawned. It
produces a structured trace that downstream rules can query — most
importantly, "was the benchmark's test runner ever invoked?".
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class ProcessEvent(BaseModel):
    """A single observed process spawn."""

    pid: int | None = None
    argv: list[str]
    cwd: Path | None = None
    started_at: datetime | None = None
    exit_code: int | None = None
    duration_ms: float | None = None


class ProcessTrace(BaseModel):
    """Aggregate process trace for one trajectory replay."""

    events: list[ProcessEvent] = Field(default_factory=list)

    def invocations_of(self, program: str) -> list[ProcessEvent]:
        """Return every event whose argv[0] basename matches ``program``."""
        raise NotImplementedError("Phase 3: implement argv-basename lookup.")


class ProcessTracer:
    """Stateful tracer attached to a sandbox session."""

    def __init__(self) -> None:
        self._events: list[ProcessEvent] = []

    def attach(self, sandbox: object) -> None:
        """Hook into the sandbox so that process spawns are recorded."""
        raise NotImplementedError("Phase 3: implement docker events / ptrace integration.")

    def trace(self) -> ProcessTrace:
        """Return the accumulated trace."""
        raise NotImplementedError("Phase 3: implement trace export.")
