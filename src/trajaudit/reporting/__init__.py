"""Reporting and integrity-adjusted leaderboards.

The reporting layer consumes per-trajectory
:class:`~trajaudit.core.verdict.AuditVerdict` records and produces the
artifacts users actually look at:

* :mod:`trajaudit.reporting.leaderboard` — aggregate verdicts into an
  integrity-adjusted leaderboard plus the ``compare`` rank-diff report.
* :mod:`trajaudit.reporting.exporters` — JSON, Markdown, CSV exporters.
"""

from __future__ import annotations
