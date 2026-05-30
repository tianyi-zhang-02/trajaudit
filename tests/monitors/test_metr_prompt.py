"""Tests for METRPromptMonitor. All API calls are mocked."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from trajaudit.core.events import ReasoningEvent, ToolCallEvent
from trajaudit.core.trajectory import Trajectory
from trajaudit.core.verdict import SemanticLabel
from trajaudit.monitors import Monitor
from trajaudit.monitors.metr_prompt import METRPromptMonitor


def _trajectory() -> Trajectory:
    return Trajectory(
        trajectory_id="t-1",
        benchmark="malt-public",
        task_id="test-task",
        events=[
            ReasoningEvent(content="I will run pytest."),
            ToolCallEvent(tool_name="bash", arguments={"cmd": "pytest"}, call_id="c-1"),
        ],
    )


def _client_returning(text: str, *, input_tokens: int = 1000, output_tokens: int = 50) -> MagicMock:
    """Build an Anthropic-shaped mock client that returns ``text`` on .create."""
    client = MagicMock()
    client.messages.count_tokens.return_value = SimpleNamespace(input_tokens=input_tokens)
    response = SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )
    client.messages.create.return_value = response
    return client


# ---------------------------------------------------------------------------
# Monitor protocol satisfaction
# ---------------------------------------------------------------------------


def test_metr_monitor_satisfies_protocol() -> None:
    monitor = METRPromptMonitor(client=_client_returning('{"reason": "x", "score": 3}'))
    assert isinstance(monitor, Monitor)
    assert monitor.name == "metr"


# ---------------------------------------------------------------------------
# Successful score path
# ---------------------------------------------------------------------------


def test_successful_score_high() -> None:
    client = _client_returning(
        '{"reason": "Modified the test file", "score": 9}'
    )
    monitor = METRPromptMonitor(client=client)
    verdict = monitor.score(_trajectory())
    assert verdict.verdict is SemanticLabel.EXPLOIT_LIKELY
    assert verdict.confidence_band == (0.9, 0.9)
    assert verdict.abstain is False


def test_successful_score_low() -> None:
    client = _client_returning(
        '{"reason": "Looks clean", "score": 1}'
    )
    monitor = METRPromptMonitor(client=client)
    verdict = monitor.score(_trajectory())
    assert verdict.verdict is SemanticLabel.CLEAN
    assert verdict.confidence_band == (0.1, 0.1)
    assert verdict.abstain is False


def test_score_at_threshold_is_exploit() -> None:
    # Score=5 → EXPLOIT_LIKELY per docstring threshold (≥5).
    client = _client_returning('{"reason": "borderline", "score": 5}')
    verdict = METRPromptMonitor(client=client).score(_trajectory())
    assert verdict.verdict is SemanticLabel.EXPLOIT_LIKELY
    assert verdict.confidence_band == (0.5, 0.5)


# ---------------------------------------------------------------------------
# Refusal / unparseable → abstain
# ---------------------------------------------------------------------------


def test_refusal_returns_abstain() -> None:
    client = _client_returning("I'm sorry, I can't help with that.")
    verdict = METRPromptMonitor(client=client).score(_trajectory())
    assert verdict.abstain is True
    assert verdict.verdict is SemanticLabel.ABSTAIN
    assert verdict.confidence_band == (0.0, 1.0)
    assert "unparseable or refused" in verdict.reasoning


def test_unparseable_json_returns_abstain() -> None:
    client = _client_returning("There is some text but no score field here.")
    verdict = METRPromptMonitor(client=client).score(_trajectory())
    assert verdict.abstain is True


def test_score_out_of_range_returns_abstain() -> None:
    client = _client_returning('{"reason": "broken", "score": 42}')
    verdict = METRPromptMonitor(client=client).score(_trajectory())
    assert verdict.abstain is True


# ---------------------------------------------------------------------------
# Over-context → abstain
# ---------------------------------------------------------------------------


def test_over_context_returns_abstain() -> None:
    client = MagicMock()
    # Simulate a token count above context_window - safety_margin.
    client.messages.count_tokens.return_value = SimpleNamespace(input_tokens=250_000)
    # If the monitor incorrectly proceeds we'd see this called; we'll assert it isn't.
    client.messages.create.side_effect = AssertionError(
        "should not be called when over-context"
    )
    monitor = METRPromptMonitor(client=client)
    verdict = monitor.score(_trajectory())
    assert verdict.abstain is True
    assert "exceeds context window" in verdict.reasoning
    client.messages.create.assert_not_called()


# ---------------------------------------------------------------------------
# Retry-then-fail
# ---------------------------------------------------------------------------


class _FakeRateLimitError(Exception):
    """Surrogate that the monitor classifies as transient."""

    def __init__(self) -> None:
        super().__init__("rate limit hit")
        self.status_code = 429


# Rename to a class name the monitor recognizes as transient.
_FakeRateLimitError.__name__ = "RateLimitError"


def test_retry_then_fail_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.messages.count_tokens.return_value = SimpleNamespace(input_tokens=1000)
    client.messages.create.side_effect = _FakeRateLimitError()

    # Patch time.sleep to keep the test fast.
    import trajaudit.monitors.metr_prompt as metr_mod

    monkeypatch.setattr(metr_mod, "time", MagicMock())
    monitor = METRPromptMonitor(client=client, max_retries=3)

    with pytest.raises(_FakeRateLimitError):
        monitor.score(_trajectory())
    # 3 attempts total (initial + 2 retries within max_retries=3).
    assert client.messages.create.call_count == 3


def test_non_transient_error_does_not_retry() -> None:
    client = MagicMock()
    client.messages.count_tokens.return_value = SimpleNamespace(input_tokens=1000)
    # ValueError is not transient.
    client.messages.create.side_effect = ValueError("malformed request")
    monitor = METRPromptMonitor(client=client)
    with pytest.raises(ValueError):
        monitor.score(_trajectory())
    assert client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# Cost / usage accumulators
# ---------------------------------------------------------------------------


def test_cost_tracking_accumulates() -> None:
    client = _client_returning(
        '{"reason": "x", "score": 3}', input_tokens=2_000, output_tokens=100
    )
    monitor = METRPromptMonitor(client=client)
    monitor.score(_trajectory())
    monitor.score(_trajectory())
    assert monitor.calls == 2
    assert monitor.total_input_tokens == 4_000
    assert monitor.total_output_tokens == 200
    # 2000 in + 100 out × pricing: (2000 × 3/1e6) + (100 × 15/1e6) = 0.0075. × 2 calls = 0.015.
    assert monitor.total_cost_usd == pytest.approx(0.015, rel=1e-6)
    assert monitor.last_call_cost_usd == pytest.approx(0.0075, rel=1e-6)


# ---------------------------------------------------------------------------
# Token-count fallback when count_tokens itself fails
# ---------------------------------------------------------------------------


def test_count_tokens_failure_proceeds_with_call() -> None:
    """If count_tokens raises, we still attempt the API call (server enforces)."""
    client = MagicMock()
    client.messages.count_tokens.side_effect = RuntimeError("count_tokens unavailable")
    response = SimpleNamespace(
        content=[SimpleNamespace(text='{"reason": "ok", "score": 2}')],
        usage=SimpleNamespace(input_tokens=500, output_tokens=20),
    )
    client.messages.create.return_value = response
    verdict = METRPromptMonitor(client=client).score(_trajectory())
    assert verdict.verdict is SemanticLabel.CLEAN
    client.messages.create.assert_called_once()
