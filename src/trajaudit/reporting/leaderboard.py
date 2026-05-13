"""Integrity-adjusted leaderboard aggregation.

A :class:`LeaderboardEntry` summarizes one agent's performance on one
benchmark with three numbers:

* ``raw_pass_rate`` — what the harness reported.
* ``clean_pass_rate`` — fraction of trajectories with
  :attr:`~trajaudit.core.verdict.IntegrityLabel.CLEAN`.
* ``non_exploit_pass_rate`` — pass rate after stripping only
  trajectories labeled
  :attr:`~trajaudit.core.verdict.IntegrityLabel.EXPLOIT`.

The gap between ``raw_pass_rate`` and ``clean_pass_rate`` is the
headline diagnostic TrajAudit exists to surface. ``n_uncertain``
makes explicit how much of the population the framework declined to
classify either way.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from trajaudit.core.verdict import AuditVerdict


class LeaderboardEntry(BaseModel):
    """One row of an integrity-adjusted leaderboard."""

    agent_id: str
    benchmark: str
    n_tasks: int
    raw_pass_rate: float = Field(..., ge=0.0, le=1.0)
    clean_pass_rate: float = Field(..., ge=0.0, le=1.0)
    non_exploit_pass_rate: float = Field(..., ge=0.0, le=1.0)
    n_exploits: int = 0
    n_suspect: int = 0
    n_uncertain: int = 0


class IntegrityLeaderboard(BaseModel):
    """An integrity-adjusted leaderboard for one benchmark."""

    benchmark: str
    entries: list[LeaderboardEntry] = Field(default_factory=list)

    @classmethod
    def build(cls, verdicts: list[AuditVerdict]) -> IntegrityLeaderboard:
        """Aggregate per-trajectory verdicts into a leaderboard."""
        raise NotImplementedError("Phase 5: implement leaderboard aggregation.")


class ComparisonReport(BaseModel):
    """Output of ``trajaudit compare`` — two submissions side-by-side."""

    benchmark: str
    submission_a: LeaderboardEntry
    submission_b: LeaderboardEntry
    raw_rank_diff: int = Field(
        ..., description="rank(B) - rank(A) by raw_pass_rate."
    )
    integrity_rank_diff: int = Field(
        ..., description="rank(B) - rank(A) by clean_pass_rate."
    )
    rationale: str

    @classmethod
    def build(
        cls,
        *,
        benchmark: str,
        verdicts_a: list[AuditVerdict],
        verdicts_b: list[AuditVerdict],
    ) -> ComparisonReport:
        """Build the comparison between two submissions on one benchmark."""
        raise NotImplementedError("Phase 5: implement comparison report.")
