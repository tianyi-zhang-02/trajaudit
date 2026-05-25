"""Typed event variants for the unified Trajectory event stream.

Each event in a :class:`~trajaudit.core.trajectory.Trajectory` is one of
four discriminated variants — :class:`ReasoningEvent`,
:class:`ToolCallEvent`, :class:`ObservationEvent`, :class:`ScoringEvent`.
The discriminator is the literal ``event_type`` field on each variant;
the :data:`TrajectoryEvent` annotated union is the Pydantic-aware form
that benchmark adapters, layers, and monitor adapters all consume.

The unified stream replaces the earlier parallel lists
(``steps`` / ``file_edits`` / ``shell_commands``) which lost interleaving
order across the three lists. Monitor adapters such as METR, EvilGenie,
and Meerkat all operate on the *interleaved* sequence, so the data
model preserves it natively.

:class:`ToolCallEvent` and :class:`ObservationEvent` are linked by
``call_id``: when a tool call is observed, the originating
:class:`ToolCallEvent` and the resulting :class:`ObservationEvent`
share a non-None ``call_id``. Adapters that cannot recover a stable id
may leave both fields ``None``; in that case
:meth:`~trajaudit.core.trajectory.Trajectory.paired_calls` yields
``(call, None)`` for the unmatched call.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class ReasoningEvent(BaseModel):
    """The model's chain-of-thought or scratchpad content."""

    event_type: Literal["reasoning"] = "reasoning"
    content: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallEvent(BaseModel):
    """The agent invoking a tool.

    ``call_id`` (when non-None) is the join key to the matching
    :class:`ObservationEvent`.
    """

    event_type: Literal["tool_call"] = "tool_call"
    tool_name: str
    arguments: dict[str, Any]
    call_id: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObservationEvent(BaseModel):
    """The environment's response to a tool call or other external event.

    ``source`` is a free-form classifier (``"stdout"``, ``"tool_result"``,
    ``"file_diff"``, ``"error"``, …). ``call_id`` (when non-None) joins
    back to the originating :class:`ToolCallEvent`.
    """

    event_type: Literal["observation"] = "observation"
    content: str
    source: str | None = None
    call_id: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoringEvent(BaseModel):
    """An eval-time scoring/grading event emitted by the harness."""

    event_type: Literal["scoring"] = "scoring"
    score: float | None = None
    passed: bool | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


TrajectoryEvent = Annotated[
    ReasoningEvent | ToolCallEvent | ObservationEvent | ScoringEvent,
    Field(discriminator="event_type"),
]
"""Discriminated union of all valid trajectory event variants.

Pydantic resolves the variant from the literal ``event_type`` field on
each member, so consumers can use ``isinstance(e, ToolCallEvent)`` etc.
directly after deserialization.
"""
