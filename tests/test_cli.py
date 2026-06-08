"""Tests for the v0.1 ``monitorstress run`` CLI.

Both the MALT loader and the METR monitor are monkey-patched so the
tests are hermetic (no HF auth, no API calls).
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from monitorstress.cli import app
from monitorstress.core.events import ReasoningEvent, ScoringEvent, ToolCallEvent
from monitorstress.core.trajectory import Trajectory
from monitorstress.core.verdict import SemanticLabel, SemanticVerdict

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _fake_trajectory(idx: int, *, positive: bool) -> Trajectory:
    label = "bypass_constraints" if positive else "normal"
    return Trajectory(
        trajectory_id=f"fake-{idx:03d}",
        benchmark="malt-public",
        task_id=f"task-{idx}",
        events=[
            ReasoningEvent(content=f"reasoning for {idx}"),
            ToolCallEvent(tool_name="bash", arguments={"cmd": "ls"}, call_id=f"c-{idx}"),
            ScoringEvent(score=1.0 if not positive else 0.0, passed=not positive),
        ],
        metadata={"labels": [label], "manually_reviewed": True},
    )


def _fake_load_malt_split_factory(n_pos: int, n_neg: int):
    """Returns a function compatible with load_malt_split's signature."""

    def fake_loader(
        split: str = "public",
        subset: str = "manually_reviewed",
        limit: int | None = None,
    ) -> Iterator[Trajectory]:
        positives = [_fake_trajectory(i, positive=True) for i in range(n_pos)]
        negatives = [_fake_trajectory(i + 1000, positive=False) for i in range(n_neg)]
        yield from positives + negatives

    return fake_loader


class _FakeMonitor:
    """Stand-in for METRPromptMonitor — perfect classifier on label."""

    name = "metr"

    def __init__(self, *, abstain_rate: float = 0.0, cost_per_call: float = 0.01) -> None:
        self._abstain_rate = abstain_rate
        self._cost_per_call = cost_per_call
        self._rng = random.Random(0)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.last_call_cost_usd = 0.0
        self.calls = 0

    def score(self, trajectory: Trajectory) -> SemanticVerdict:
        self.calls += 1
        self.last_call_cost_usd = self._cost_per_call
        self.total_cost_usd += self._cost_per_call
        # Abstain a fraction of the time.
        if self._rng.random() < self._abstain_rate:
            return SemanticVerdict(
                verdict=SemanticLabel.ABSTAIN,
                confidence_band=(0.0, 1.0),
                reasoning="forced abstain in test",
                abstain=True,
                escalated_from=None,
            )
        # Perfect classifier on ground truth label.
        labels = trajectory.metadata.get("labels", [])
        is_positive = labels and labels != ["normal"]
        p = 0.9 if is_positive else 0.1
        label = SemanticLabel.EXPLOIT_LIKELY if p >= 0.5 else SemanticLabel.CLEAN
        return SemanticVerdict(
            verdict=label,
            confidence_band=(p, p),
            reasoning="fake monitor",
            escalated_from=None,
        )


# ---------------------------------------------------------------------------
# Input-validation paths
# ---------------------------------------------------------------------------


def test_unsupported_monitor_exits_with_2() -> None:
    result = runner.invoke(app, ["run", "--monitor", "evilgenie"])
    assert result.exit_code == 2
    assert "evilgenie" in result.stdout


def test_limit_over_hard_cap_exits_with_2() -> None:
    result = runner.invoke(app, ["run", "--limit", "9999"])
    assert result.exit_code == 2
    assert "1000" in result.stdout


def test_bad_subset_exits_with_2() -> None:
    result = runner.invoke(app, ["run", "--subset", "nonsense"])
    assert result.exit_code == 2


def test_nonpositive_budget_exits_with_2() -> None:
    result = runner.invoke(app, ["run", "--budget-usd", "0"])
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def _patch_cli(monkeypatch: pytest.MonkeyPatch, monitor: _FakeMonitor, *, n_pos: int = 20, n_neg: int = 20) -> None:
    import monitorstress.cli as cli_mod

    monkeypatch.setattr(cli_mod, "load_malt_split", _fake_load_malt_split_factory(n_pos, n_neg))
    monkeypatch.setattr(cli_mod, "METRPromptMonitor", lambda: monitor)


def test_happy_path_writes_records_and_prints_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = _FakeMonitor()
    _patch_cli(monkeypatch, fake)
    output = tmp_path / "run.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--monitor", "metr",
            "--limit", "20",
            "--budget-usd", "10.0",
            "--output", str(output),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "report card" in result.stdout.lower()
    # 20 trajectories × 4 variants = 80 monitor calls.
    assert fake.calls == 80
    assert output.exists()
    payload = json.loads(output.read_text())
    assert "records" in payload
    assert "report" in payload
    assert len(payload["records"]) == 80


def test_budget_cap_aborts_cleanly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # cost_per_call=$0.50 × 4 variants per trajectory = $2 per trajectory.
    # Budget $3.00 should stop after the SECOND trajectory completes.
    # (After traj 1: spend $2.00, < $3.00, continue. After traj 2: spend $4.00, >= $3.00,
    # next iteration sees the cap and stops; so 2 trajectories × 4 variants = 8 records.)
    fake = _FakeMonitor(cost_per_call=0.50)
    _patch_cli(monkeypatch, fake, n_pos=10, n_neg=10)
    output = tmp_path / "run.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--limit", "20",
            "--budget-usd", "3.00",
            "--output", str(output),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Budget cap reached" in result.stdout
    payload = json.loads(output.read_text())
    # Partial results: between 4 and 12 records (depends on exact stop point).
    assert 4 <= len(payload["records"]) <= 12


def test_default_output_path_uses_timestamp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = _FakeMonitor()
    _patch_cli(monkeypatch, fake, n_pos=5, n_neg=5)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app, ["run", "--limit", "10", "--budget-usd", "10.0"]
    )
    assert result.exit_code == 0
    written = list(tmp_path.glob("trajaudit_run_*.json"))
    assert len(written) == 1


def test_abstain_records_are_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = _FakeMonitor(abstain_rate=1.0)  # always abstain
    _patch_cli(monkeypatch, fake, n_pos=5, n_neg=5)
    output = tmp_path / "run.json"
    result = runner.invoke(
        app, ["run", "--limit", "10", "--budget-usd", "10.0", "--output", str(output)]
    )
    assert result.exit_code == 0
    payload = json.loads(output.read_text())
    assert all(r["abstain"] is True for r in payload["records"])


# ---------------------------------------------------------------------------
# Balance warning
# ---------------------------------------------------------------------------


def test_imbalanced_dataset_logs_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Only 5 positives but 20 requested per class → warning surfaces.
    fake = _FakeMonitor()
    _patch_cli(monkeypatch, fake, n_pos=5, n_neg=50)
    output = tmp_path / "run.json"
    result = runner.invoke(
        app,
        ["run", "--limit", "40", "--budget-usd", "10.0", "--output", str(output)],
    )
    assert result.exit_code == 0
    assert "balance not fully achieved" in result.stdout.lower() \
        or "+5 / -" in result.stdout  # one of these always appears
