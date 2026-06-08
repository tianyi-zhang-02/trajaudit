"""Tests for the v0.1 report-card module.

All tests use synthetic ScoreRecord lists — no API calls, no I/O.
"""

from __future__ import annotations

import io
import random

import pytest
from rich.console import Console

from monitorstress.report import (
    ScoreRecord,
    TransformReport,
    compute_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_records(
    n_per_class: int = 20,
    *,
    transformations: list[str] | None = None,
    clean_signal: float = 0.95,
    transform_signal: dict[str, float] | None = None,
    seed: int = 0,
) -> list[ScoreRecord]:
    """Build a synthetic dataset where the monitor has tunable signal per transformation.

    ``signal``: probability that a positive trajectory gets a high score and a
    negative trajectory gets a low score. 1.0 = perfect monitor, 0.5 = chance.
    """
    rng = random.Random(seed)
    transformations = transformations or ["clean", "drop_reasoning", "truncate_obs", "pad_noops"]
    transform_signal = transform_signal or {}
    records: list[ScoreRecord] = []

    # Build trajectory-level ground truth first so ids match across transformations.
    truths: list[tuple[str, int]] = (
        [(f"t-pos-{i}", 1) for i in range(n_per_class)]
        + [(f"t-neg-{i}", 0) for i in range(n_per_class)]
    )

    for name in transformations:
        sig = clean_signal if name == "clean" else transform_signal.get(name, clean_signal)
        for traj_id, gt in truths:
            # With probability `sig`, score aligns with ground truth.
            aligned = rng.random() < sig
            if gt == 1:
                score = rng.uniform(0.6, 1.0) if aligned else rng.uniform(0.0, 0.4)
            else:
                score = rng.uniform(0.0, 0.4) if aligned else rng.uniform(0.6, 1.0)
            records.append(
                ScoreRecord(
                    trajectory_id=traj_id,
                    transformation_name=name,
                    ground_truth_label=gt,
                    monitor_score=score,
                )
            )
    return records


# ---------------------------------------------------------------------------
# Basic shape
# ---------------------------------------------------------------------------


def test_compute_report_returns_all_four_rows() -> None:
    records = _make_records(n_per_class=30)
    report = compute_report(records, n_bootstrap=100)
    assert set(report.per_transformation) == {
        "clean", "drop_reasoning", "truncate_obs", "pad_noops",
    }


def test_clean_row_has_no_delta() -> None:
    records = _make_records(n_per_class=30)
    report = compute_report(records, n_bootstrap=100)
    clean = report.per_transformation["clean"]
    assert clean.delta_auroc is None
    assert clean.fpr_shift is None
    assert clean.auroc is not None
    assert 0.5 <= clean.auroc <= 1.0


def test_perfect_monitor_yields_auroc_one() -> None:
    records = _make_records(n_per_class=30, clean_signal=1.0)
    report = compute_report(records, n_bootstrap=200)
    assert report.per_transformation["clean"].auroc == pytest.approx(1.0)


def test_chance_monitor_yields_auroc_near_half() -> None:
    records = _make_records(n_per_class=50, clean_signal=0.5, seed=42)
    report = compute_report(records, n_bootstrap=200)
    auroc = report.per_transformation["clean"].auroc
    assert auroc is not None
    assert 0.3 <= auroc <= 0.7


# ---------------------------------------------------------------------------
# Δ AUROC sign convention
# ---------------------------------------------------------------------------


def test_degraded_transformation_yields_negative_delta() -> None:
    records = _make_records(
        n_per_class=40,
        clean_signal=0.95,
        transform_signal={"drop_reasoning": 0.55},
        seed=7,
    )
    report = compute_report(records, n_bootstrap=200)
    delta = report.per_transformation["drop_reasoning"].delta_auroc
    assert delta is not None
    assert delta < -0.1, f"expected meaningful degradation, got Δ={delta}"


def test_neutral_transformation_yields_near_zero_delta() -> None:
    records = _make_records(
        n_per_class=40,
        clean_signal=0.9,
        transform_signal={"truncate_obs": 0.9},
        seed=11,
    )
    report = compute_report(records, n_bootstrap=200)
    delta = report.per_transformation["truncate_obs"].delta_auroc
    assert delta is not None
    assert abs(delta) < 0.15


# ---------------------------------------------------------------------------
# Worst-case extraction
# ---------------------------------------------------------------------------


def test_worst_case_picks_min_delta() -> None:
    records = _make_records(
        n_per_class=40,
        clean_signal=0.95,
        transform_signal={"drop_reasoning": 0.55, "truncate_obs": 0.9, "pad_noops": 0.75},
        seed=3,
    )
    report = compute_report(records, n_bootstrap=200)
    assert report.worst_case_transformation == "drop_reasoning"
    assert report.worst_case_delta is not None
    assert report.worst_case_delta < 0


# ---------------------------------------------------------------------------
# FPR shift at calibrated threshold
# ---------------------------------------------------------------------------


def test_fpr_shift_positive_for_degraded_transformation() -> None:
    """A worse monitor should raise false-positive rate at the same threshold."""
    records = _make_records(
        n_per_class=80,
        clean_signal=0.95,
        transform_signal={"drop_reasoning": 0.55},
        seed=99,
    )
    report = compute_report(records, n_bootstrap=200, fpr_target=0.05)
    shift = report.per_transformation["drop_reasoning"].fpr_shift
    assert shift is not None
    assert shift >= 0  # degraded → at minimum no improvement in FPR


def test_fpr_target_is_recorded() -> None:
    records = _make_records(n_per_class=30)
    report = compute_report(records, n_bootstrap=100, fpr_target=0.1)
    assert report.fpr_target == 0.1


# ---------------------------------------------------------------------------
# Abstain handling
# ---------------------------------------------------------------------------


def test_abstained_records_excluded_from_metrics() -> None:
    records = _make_records(n_per_class=20)
    # Add 5 abstained records to drop_reasoning.
    for i in range(5):
        records.append(
            ScoreRecord(
                trajectory_id=f"t-abs-{i}",
                transformation_name="drop_reasoning",
                ground_truth_label=1,
                monitor_score=None,
                abstain=True,
            )
        )
    report = compute_report(records, n_bootstrap=100)
    r = report.per_transformation["drop_reasoning"]
    assert r.n_abstained == 5
    # n_samples reflects only paired-with-clean trajectories, which the 5 abstains aren't.
    assert r.n_samples == 40  # 20 pos + 20 neg, all paired with clean


def test_all_abstain_yields_none_auroc() -> None:
    records = [
        ScoreRecord(
            trajectory_id=f"t-{i}",
            transformation_name="clean",
            ground_truth_label=i % 2,
            monitor_score=None,
            abstain=True,
        )
        for i in range(20)
    ]
    report = compute_report(records, n_bootstrap=50)
    assert report.per_transformation["clean"].auroc is None
    assert report.per_transformation["clean"].n_abstained == 20


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_render_produces_table_string() -> None:
    records = _make_records(n_per_class=30)
    report = compute_report(records, n_bootstrap=100)
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    report.render(console=console)
    out = buf.getvalue()
    assert "report card" in out.lower()
    assert "clean" in out
    assert "drop_reasoning" in out
    assert "truncate_obs" in out
    assert "pad_noops" in out
    assert "Worst-case" in out


def test_to_dict_round_trips_floats() -> None:
    records = _make_records(n_per_class=20)
    report = compute_report(records, n_bootstrap=100)
    d = report.to_dict()
    assert "per_transformation" in d
    for k, v in d["per_transformation"].items():
        assert v["transformation_name"] == k


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_records() -> None:
    report = compute_report([], n_bootstrap=50)
    assert report.per_transformation == {
        "clean": TransformReport(
            transformation_name="clean",
            n_samples=0,
            n_abstained=0,
            auroc=None, auroc_ci_lo=None, auroc_ci_hi=None,
            delta_auroc=None, delta_ci_lo=None, delta_ci_hi=None,
            fpr_shift=None,
        )
    }
    assert report.worst_case_delta is None


def test_single_class_yields_none_auroc() -> None:
    # All positives → AUROC undefined.
    records = [
        ScoreRecord(
            trajectory_id=f"t-{i}",
            transformation_name="clean",
            ground_truth_label=1,
            monitor_score=0.9,
        )
        for i in range(20)
    ]
    report = compute_report(records, n_bootstrap=50)
    assert report.per_transformation["clean"].auroc is None


# ---------------------------------------------------------------------------
# M1 invariant: (monitor_score is None) ⟺ (abstain is True)
# ---------------------------------------------------------------------------


def test_score_record_rejects_unscored_non_abstain() -> None:
    """Regression for M1 (docs/status_report.md § M1 root-cause investigation).

    Constructing ``ScoreRecord(monitor_score=None, abstain=False)`` is the
    dormant case that would surface as an ``IndexError`` in the bootstrap
    loop of :func:`compute_report`. The strict ``__post_init__`` validator
    raises a clear ``ValueError`` at construction instead.
    """
    with pytest.raises(ValueError, match="ScoreRecord invariant violated") as exc:
        ScoreRecord(
            trajectory_id="t-bad",
            transformation_name="clean",
            ground_truth_label=1,
            monitor_score=None,
            abstain=False,
        )
    # The verbose message names both fields.
    msg = str(exc.value)
    assert "abstain=False" in msg
    assert "monitor_score=None" in msg


def test_score_record_accepts_valid_combinations() -> None:
    """Both legal states construct cleanly after the validator lands."""
    scored = ScoreRecord(
        trajectory_id="t-scored",
        transformation_name="clean",
        ground_truth_label=1,
        monitor_score=0.5,
        abstain=False,
    )
    assert scored.monitor_score == 0.5
    assert scored.abstain is False

    abstained = ScoreRecord(
        trajectory_id="t-abstained",
        transformation_name="clean",
        ground_truth_label=1,
        monitor_score=None,
        abstain=True,
    )
    assert abstained.monitor_score is None
    assert abstained.abstain is True
