"""MALT ingestion adapter.

Loads `metr-evals/malt-public <https://huggingface.co/datasets/metr-evals/malt-public>`_
(the ordered-messages variant of MALT) and converts each transcript row into a
:class:`~trajaudit.core.trajectory.Trajectory` populated with discriminated
:data:`~trajaudit.core.events.TrajectoryEvent` variants.

Auth: the dataset is gated. Callers must (1) accept the dataset terms on
HuggingFace, (2) generate a read token, and (3) export ``HF_TOKEN`` in the
environment. :func:`load_malt_split` raises a clear error if ``HF_TOKEN`` is
absent rather than silently returning an empty iterator.

Schema assumptions
==================
The HF dataset card describes each row as carrying ``metadata`` and ``samples``
(a list of input/output message lists). The exact column layout was not
inspectable in the session this adapter was authored (HF token blocked); the
field names below are taken from the public dataset-card description. If
MALT's on-disk schema diverges, the field-extraction helpers
(``_event_from_block``, ``_extract_scoring``) are the only things that need to
change — the Trajectory-level mapping is stable.

Two specific schema conventions we adopt:

* **Message content.** Each message is either ``{"role": str, "content": str}``
  (legacy form, where the string carries free-form assistant text or a user
  turn) or ``{"role": str, "content": [...blocks...]}`` (modern form, where
  each block has a ``type`` of ``text``, ``tool_use``, or ``tool_result``).
  Both shapes are supported.
* **Call IDs.** When MALT exposes Anthropic-style ``tool_use`` IDs we
  preserve them. When it does not we synthesize deterministic ids of the form
  ``f"{transcript_id}-{call_index}"`` per the v0.1 spec.

Timestamps
==========
MALT carries no per-event timestamps. We synthesize a strictly monotone
timestamp by adding ``index * 1 second`` to the fixed epoch
``2025-01-01T00:00:00Z``. The synthesized timestamps are useful for ordering
and debugging but should not be read as wall-clock times — the epoch is
documented here so downstream code can detect it (``ts.year == 2025`` plus
``ts.microsecond == 0`` is a reliable test).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from trajaudit.core.events import (
    ObservationEvent,
    ReasoningEvent,
    ScoringEvent,
    ToolCallEvent,
    TrajectoryEvent,
)
from trajaudit.core.trajectory import HarnessResult, Trajectory

# Synthetic-timestamp epoch. Document in module docstring above.
_SYNTH_EPOCH = datetime(2025, 1, 1, tzinfo=UTC)


def _synthetic_ts(index: int) -> datetime:
    return _SYNTH_EPOCH + timedelta(seconds=index)


def _coerce_text(block_or_string: Any) -> str:
    """Best-effort string extraction from an Anthropic-style content block."""
    if isinstance(block_or_string, str):
        return block_or_string
    if isinstance(block_or_string, dict):
        for key in ("text", "content", "value"):
            if key in block_or_string and isinstance(block_or_string[key], str):
                return block_or_string[key]
        return str(block_or_string)
    return str(block_or_string)


def _normalize_content(content: Any) -> list[dict[str, Any]]:
    """Return content as a list of block dicts regardless of input shape.

    String content is wrapped as a single ``{"type": "text", "text": ...}`` block.
    """
    if content is None:
        return []
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [b if isinstance(b, dict) else {"type": "text", "text": _coerce_text(b)} for b in content]
    if isinstance(content, dict):
        return [content]
    return [{"type": "text", "text": _coerce_text(content)}]


def _events_from_messages(
    messages: list[dict[str, Any]],
    *,
    transcript_id: str,
    start_index: int = 0,
) -> tuple[list[TrajectoryEvent], int]:
    """Convert a list of MALT messages to ``TrajectoryEvent`` instances.

    Returns ``(events, next_index)`` so a caller can chain multiple message
    lists (e.g., ``input_messages`` followed by ``output_messages``) while
    keeping the synthesized timestamps monotone.

    Mapping rules:

    * ``role == "system"`` or the first ``role == "user"`` text-only message
      is treated as task framing and does not emit an event.
    * ``role == "assistant"`` with text blocks → :class:`ReasoningEvent` per
      text block (one event each, preserving order).
    * ``role == "assistant"`` with ``tool_use`` blocks → :class:`ToolCallEvent`
      with ``call_id`` copied from the block when present.
    * ``role == "user"`` (or ``"tool"``) with ``tool_result`` blocks →
      :class:`ObservationEvent` with ``call_id`` linked back to the original
      tool call.

    Any block whose ``type`` we don't recognize is folded into a
    :class:`ReasoningEvent` so no content is silently lost.
    """
    events: list[TrajectoryEvent] = []
    index = start_index
    synthesized_call_counter = 0
    framing_consumed = False

    for msg in messages:
        role = msg.get("role")
        blocks = _normalize_content(msg.get("content"))

        # Treat the first system/user message that is pure text as task framing.
        if not framing_consumed and role in ("system", "user") and all(
            b.get("type", "text") == "text" for b in blocks
        ):
            framing_consumed = True
            continue

        for block in blocks:
            btype = block.get("type", "text")
            ts = _synthetic_ts(index)

            if role == "assistant" and btype == "text":
                events.append(
                    ReasoningEvent(content=_coerce_text(block), timestamp=ts)
                )
            elif role == "assistant" and btype == "tool_use":
                call_id = block.get("id")
                if call_id is None:
                    call_id = f"{transcript_id}-{synthesized_call_counter}"
                    synthesized_call_counter += 1
                events.append(
                    ToolCallEvent(
                        tool_name=block.get("name", "unknown"),
                        arguments=dict(block.get("input", {})),
                        call_id=str(call_id),
                        timestamp=ts,
                    )
                )
            elif btype == "tool_result" or (role in ("user", "tool") and btype != "text"):
                call_id = block.get("tool_use_id") or block.get("call_id")
                events.append(
                    ObservationEvent(
                        content=_coerce_text(block.get("content", block)),
                        source="tool_result",
                        call_id=str(call_id) if call_id is not None else None,
                        timestamp=ts,
                    )
                )
            elif role in ("user", "tool") and btype == "text":
                events.append(
                    ObservationEvent(
                        content=_coerce_text(block),
                        source="stdout",
                        timestamp=ts,
                    )
                )
            else:
                # Unrecognized block — preserve as reasoning so nothing is lost.
                events.append(
                    ReasoningEvent(
                        content=f"[unrecognized {role}/{btype}] {_coerce_text(block)}",
                        timestamp=ts,
                    )
                )
            index += 1

    return events, index


def _extract_scoring(
    row: dict[str, Any], *, start_index: int
) -> tuple[list[ScoringEvent], HarnessResult | None]:
    """Pull harness scoring out of a MALT row, if present.

    Looks at common keys: ``scoring``, ``harness_result``, ``score``. Returns
    a list (possibly empty) of :class:`ScoringEvent` plus a
    :class:`HarnessResult` for the trajectory-level convenience field.
    """
    score_dict = row.get("scoring") or row.get("harness_result")
    if not isinstance(score_dict, dict):
        return [], None

    passed = score_dict.get("passed")
    score = score_dict.get("score")
    events = [
        ScoringEvent(
            score=float(score) if isinstance(score, (int, float)) else None,
            passed=bool(passed) if passed is not None else None,
            details={k: v for k, v in score_dict.items() if k not in ("passed", "score")},
            timestamp=_synthetic_ts(start_index),
        )
    ]
    harness = (
        HarnessResult(
            passed=bool(passed),
            score=float(score) if isinstance(score, (int, float)) else None,
            raw=score_dict,
        )
        if passed is not None
        else None
    )
    return events, harness


def malt_row_to_trajectory(row: dict[str, Any]) -> Trajectory:
    """Convert one MALT row (ordered-messages format) into a :class:`Trajectory`.

    For v0.1 we take ``samples[0]`` only; rows with N-completion samples
    contribute their first completion. MALT-level labels and reviewer flags
    are carried in ``Trajectory.metadata`` (not in the event stream) per the
    v0.1 spec — labels are ground truth about the trajectory, not events
    within it.
    """
    samples = row.get("samples") or []
    if not samples:
        raise ValueError(f"MALT row has no samples: {row.get('id')!r}")
    sample = samples[0]

    transcript_id = str(row.get("id") or row.get("transcript_id") or row.get("task_id") or "unknown")

    input_messages = sample.get("input_messages") or []
    output_messages = sample.get("output_messages") or []

    events, idx = _events_from_messages(
        input_messages, transcript_id=transcript_id, start_index=0
    )
    out_events, idx = _events_from_messages(
        output_messages, transcript_id=transcript_id, start_index=idx
    )
    events.extend(out_events)

    score_events, harness = _extract_scoring(row, start_index=idx)
    events.extend(score_events)

    metadata: dict[str, Any] = {
        "labels": list(row.get("labels") or []),
        "manually_reviewed": bool(row.get("manually_reviewed", False)),
        "run_source": row.get("run_source"),
        "has_chain_of_thought": bool(row.get("has_chain_of_thought", False)),
    }
    # Pass through anything else the caller may want under a nested key.
    for key in ("count", "task_family"):
        if key in row:
            metadata[key] = row[key]

    return Trajectory(
        trajectory_id=transcript_id,
        benchmark="malt-public",
        task_id=str(row.get("task_id") or "unknown"),
        agent_id=str(row.get("model")) if row.get("model") is not None else None,
        events=events,
        harness_result=harness,
        workspace_root=None,
        metadata=metadata,
    )


def load_malt_split(
    split: str = "public",
    subset: Literal["all", "manually_reviewed"] = "manually_reviewed",
    limit: int | None = None,
) -> Iterator[Trajectory]:
    """Stream :class:`Trajectory` objects from the MALT public split.

    Parameters
    ----------
    split:
        Currently only ``"public"`` is supported; passed through as the HF
        split name (``"train"``) since MALT publishes one split.
    subset:
        ``"manually_reviewed"`` (default) yields only rows with
        ``manually_reviewed=True``. ``"all"`` yields every row including the
        presumed-benign unreviewed runs (which have a ~6% label-error rate
        per METR's documentation).
    limit:
        Optional cap on number of trajectories yielded.

    Raises
    ------
    RuntimeError
        If ``HF_TOKEN`` is not set in the environment. The error message
        includes the exact setup steps.
    """
    token = os.environ.get("HF_TOKEN")
    if not token:
        # Fall back to the cached token written by `hf auth login`.
        try:
            from huggingface_hub import get_token

            token = get_token()
        except Exception:  # noqa: BLE001
            token = None
    if not token:
        raise RuntimeError(
            "No HuggingFace credentials found. To use the MALT adapter, either:\n"
            "  (a) export HF_TOKEN=hf_... in your shell, or\n"
            "  (b) run `hf auth login` once (token persists in ~/.cache/huggingface/).\n"
            "Plus accept the dataset terms at "
            "https://huggingface.co/datasets/metr-evals/malt-public.\n"
            "Adapter aborts rather than returning an empty iterator so the "
            "auth failure is visible at call site."
        )

    from datasets import load_dataset  # local import: heavy dep, skip if never called

    hf_split = "train" if split == "public" else split
    ds = load_dataset("metr-evals/malt-public", split=hf_split, token=token)

    yielded = 0
    for row in ds:
        if subset == "manually_reviewed" and not row.get("manually_reviewed", False):
            continue
        yield malt_row_to_trajectory(dict(row))
        yielded += 1
        if limit is not None and yielded >= limit:
            return
