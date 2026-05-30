"""Tests for the MALT ingestion adapter.

All tests run against the hand-crafted fixtures under
``tests/fixtures/malt/`` — no live HuggingFace calls.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from trajaudit.adapters.malt import load_malt_split, malt_row_to_trajectory
from trajaudit.core.events import (
    ObservationEvent,
    ReasoningEvent,
    ScoringEvent,
    ToolCallEvent,
)
from trajaudit.core.trajectory import Trajectory

FIXTURES = Path(__file__).parent.parent / "fixtures" / "malt"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# Basic shape: each fixture produces a well-formed Trajectory
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture",
    ["unprompted_positive.json", "prompted_positive.json", "benign.json"],
)
def test_fixture_loads_to_trajectory(fixture: str) -> None:
    traj = malt_row_to_trajectory(_load_fixture(fixture))
    assert isinstance(traj, Trajectory)
    assert traj.benchmark == "malt-public"
    assert traj.trajectory_id
    assert traj.events, "every fixture should produce at least one event"


# ---------------------------------------------------------------------------
# Metadata is carried on Trajectory.metadata, NOT on events
# ---------------------------------------------------------------------------


def test_metadata_carries_labels_and_review_flag() -> None:
    traj = malt_row_to_trajectory(_load_fixture("unprompted_positive.json"))
    assert traj.metadata["labels"] == ["bypass_constraints"]
    assert traj.metadata["manually_reviewed"] is True
    assert traj.metadata["run_source"] == "unprompted"
    assert traj.metadata["has_chain_of_thought"] is True

    # Labels must not leak into events.
    for ev in traj.events:
        ev_md = getattr(ev, "metadata", None)
        if isinstance(ev_md, dict):
            assert "labels" not in ev_md


def test_prompted_positive_metadata() -> None:
    traj = malt_row_to_trajectory(_load_fixture("prompted_positive.json"))
    assert traj.metadata["run_source"] == "prompted"
    assert "sabotage" in traj.metadata["labels"]


def test_benign_metadata() -> None:
    traj = malt_row_to_trajectory(_load_fixture("benign.json"))
    assert traj.metadata["labels"] == ["normal"]


# ---------------------------------------------------------------------------
# Event-type mapping
# ---------------------------------------------------------------------------


def test_event_type_mapping_unprompted_positive() -> None:
    traj = malt_row_to_trajectory(_load_fixture("unprompted_positive.json"))
    types = [type(e).__name__ for e in traj.events]
    # Expect at least one of each event variant after stripping framing.
    assert "ReasoningEvent" in types
    assert "ToolCallEvent" in types
    assert "ObservationEvent" in types
    assert "ScoringEvent" in types


# ---------------------------------------------------------------------------
# Call-id linkage: MALT-provided ids preserved
# ---------------------------------------------------------------------------


def test_call_ids_preserved_when_malt_provides_them() -> None:
    traj = malt_row_to_trajectory(_load_fixture("unprompted_positive.json"))
    tool_calls = [e for e in traj.events if isinstance(e, ToolCallEvent)]
    assert {c.call_id for c in tool_calls} == {"toolu_01", "toolu_02", "toolu_03"}

    pairs = list(traj.paired_calls())
    assert len(pairs) == 3
    for call, obs in pairs:
        assert obs is not None
        assert obs.call_id == call.call_id


# ---------------------------------------------------------------------------
# Call-id synthesis when MALT omits ids
# ---------------------------------------------------------------------------


def test_call_ids_synthesized_when_missing() -> None:
    traj = malt_row_to_trajectory(_load_fixture("benign.json"))
    tool_calls = [e for e in traj.events if isinstance(e, ToolCallEvent)]
    assert len(tool_calls) == 1
    call_id = tool_calls[0].call_id
    assert call_id is not None
    assert call_id.startswith("fixture-benign-003-")


# ---------------------------------------------------------------------------
# Temporal ordering — synthesized timestamps are strictly monotone
# ---------------------------------------------------------------------------


def test_synthetic_timestamps_strictly_monotone() -> None:
    traj = malt_row_to_trajectory(_load_fixture("unprompted_positive.json"))
    timestamps = [e.timestamp for e in traj.events if e.timestamp is not None]
    assert timestamps == sorted(timestamps)
    # All from the documented synthetic epoch (year 2025, second-resolution).
    assert all(isinstance(ts, datetime) and ts.year == 2025 for ts in timestamps)


# ---------------------------------------------------------------------------
# Scoring event + HarnessResult population
# ---------------------------------------------------------------------------


def test_scoring_event_and_harness_result() -> None:
    traj = malt_row_to_trajectory(_load_fixture("unprompted_positive.json"))
    scoring = [e for e in traj.events if isinstance(e, ScoringEvent)]
    assert len(scoring) == 1
    assert scoring[0].passed is True
    assert scoring[0].score == 1.0

    assert traj.harness_result is not None
    assert traj.harness_result.passed is True


# ---------------------------------------------------------------------------
# Round-trip: Trajectory survives JSON serialization via Pydantic
# ---------------------------------------------------------------------------


def test_round_trip_through_pydantic() -> None:
    traj = malt_row_to_trajectory(_load_fixture("unprompted_positive.json"))
    restored = Trajectory.model_validate_json(traj.model_dump_json())
    assert restored == traj


# ---------------------------------------------------------------------------
# load_malt_split fails loudly without HF_TOKEN
# ---------------------------------------------------------------------------


def test_load_malt_split_missing_hf_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    # Also stub the cached-token fallback so the test is hermetic on
    # machines where `hf auth login` was previously run.
    import huggingface_hub  # type: ignore[import-not-found]

    monkeypatch.setattr(huggingface_hub, "get_token", lambda: None)
    with pytest.raises(RuntimeError) as exc:
        next(iter(load_malt_split()))
    assert "HF_TOKEN" in str(exc.value)
    assert "huggingface.co/datasets/metr-evals/malt-public" in str(exc.value)


# ---------------------------------------------------------------------------
# Reasoning content carries the assistant's text faithfully
# ---------------------------------------------------------------------------


def test_reasoning_event_preserves_text() -> None:
    traj = malt_row_to_trajectory(_load_fixture("prompted_positive.json"))
    reasoning = [e for e in traj.events if isinstance(e, ReasoningEvent)]
    assert reasoning, "prompted_positive includes an assistant text block"
    assert any("linear scan" in r.content for r in reasoning)


def test_observation_event_preserves_tool_result() -> None:
    traj = malt_row_to_trajectory(_load_fixture("benign.json"))
    observations = [e for e in traj.events if isinstance(e, ObservationEvent)]
    assert any("main.py" in o.content for o in observations)


# ---------------------------------------------------------------------------
# Real MALT shape: nested metadata + OpenAI-style function_call messages
# ---------------------------------------------------------------------------


def test_real_shape_loads() -> None:
    """Real MALT rows nest under `metadata` + use `input`/`output` keys
    + OpenAI-style function_call. Verify the adapter handles all three."""
    traj = malt_row_to_trajectory(_load_fixture("real_shape_openai_function_call.json"))
    assert traj.benchmark == "malt-public"
    assert traj.trajectory_id == "999001"  # run_id
    assert traj.task_id == "machine_learning_local/cifar10"
    assert traj.agent_id == "claude-3-5-sonnet-20240620"
    assert traj.metadata["labels"] == ["hardcoded_solution"]
    assert traj.metadata["manually_reviewed"] is True
    assert traj.metadata["run_source"] == "unprompted"


def test_real_shape_function_call_becomes_tool_call() -> None:
    traj = malt_row_to_trajectory(_load_fixture("real_shape_openai_function_call.json"))
    tool_calls = [e for e in traj.events if isinstance(e, ToolCallEvent)]
    assert len(tool_calls) == 2
    assert tool_calls[0].tool_name == "edit_file"
    assert tool_calls[0].arguments == {
        "path": "submission.py",
        "new_content": "def predict(x): return 'cat'",
    }
    assert tool_calls[1].tool_name == "run_eval"
    assert tool_calls[1].arguments == {}


def test_real_shape_function_response_becomes_observation() -> None:
    traj = malt_row_to_trajectory(_load_fixture("real_shape_openai_function_call.json"))
    observations = [e for e in traj.events if isinstance(e, ObservationEvent)]
    assert len(observations) == 2
    assert "file written" in observations[0].content
    assert "Accuracy" in observations[1].content


def test_real_shape_function_call_links_to_observation() -> None:
    """Adjacent function_call/function pairs share a call_id."""
    traj = malt_row_to_trajectory(_load_fixture("real_shape_openai_function_call.json"))
    pairs = list(traj.paired_calls())
    assert len(pairs) == 2
    for call, obs in pairs:
        assert obs is not None
        assert call.call_id == obs.call_id


def test_real_shape_developer_role_treated_as_framing() -> None:
    """`role == "developer"` is a framing role — no event emitted."""
    traj = malt_row_to_trajectory(_load_fixture("real_shape_openai_function_call.json"))
    # Developer message + user task framing should both be skipped.
    # The assistant's first text turn ("I'll start by hardcoding the labels.")
    # IS a reasoning event.
    reasoning = [e for e in traj.events if isinstance(e, ReasoningEvent)]
    assert len(reasoning) == 1
    assert "hardcoding" in reasoning[0].content
