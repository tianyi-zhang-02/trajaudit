"""Report exporters: JSON, Markdown, CSV.

Each exporter is a small class with a single ``write`` method. The CLI
picks the right exporter for a given output path by extension:

* ``.json`` → :class:`JSONExporter`
* ``.md`` → :class:`MarkdownExporter`
* ``.csv`` → :class:`CSVExporter`

Exporters accept either :class:`~trajaudit.core.verdict.AuditVerdict`
records, an :class:`~trajaudit.reporting.leaderboard.IntegrityLeaderboard`,
or a :class:`~trajaudit.reporting.leaderboard.ComparisonReport`, and
serialize the appropriate shape.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from trajaudit.core.verdict import AuditVerdict
from trajaudit.reporting.leaderboard import ComparisonReport, IntegrityLeaderboard


class Exporter(ABC):
    """Abstract exporter."""

    @abstractmethod
    def write_verdicts(self, verdicts: list[AuditVerdict], out_path: Path) -> None:
        """Write a list of :class:`AuditVerdict` records."""

    @abstractmethod
    def write_leaderboard(
        self, leaderboard: IntegrityLeaderboard, out_path: Path
    ) -> None:
        """Write an integrity-adjusted leaderboard."""

    @abstractmethod
    def write_comparison(self, report: ComparisonReport, out_path: Path) -> None:
        """Write a :class:`ComparisonReport`."""


class JSONExporter(Exporter):
    """JSON exporter — stable schema for downstream tooling."""

    def write_verdicts(self, verdicts: list[AuditVerdict], out_path: Path) -> None:
        raise NotImplementedError("Phase 5: implement JSON verdict export.")

    def write_leaderboard(
        self, leaderboard: IntegrityLeaderboard, out_path: Path
    ) -> None:
        raise NotImplementedError("Phase 5: implement JSON leaderboard export.")

    def write_comparison(self, report: ComparisonReport, out_path: Path) -> None:
        raise NotImplementedError("Phase 5: implement JSON comparison export.")


class MarkdownExporter(Exporter):
    """Markdown exporter — human-readable reports."""

    def write_verdicts(self, verdicts: list[AuditVerdict], out_path: Path) -> None:
        raise NotImplementedError("Phase 5: implement Markdown verdict export.")

    def write_leaderboard(
        self, leaderboard: IntegrityLeaderboard, out_path: Path
    ) -> None:
        raise NotImplementedError("Phase 5: implement Markdown leaderboard export.")

    def write_comparison(self, report: ComparisonReport, out_path: Path) -> None:
        raise NotImplementedError("Phase 5: implement Markdown comparison export.")


class CSVExporter(Exporter):
    """CSV exporter — flat row-per-trajectory for spreadsheet consumers."""

    def write_verdicts(self, verdicts: list[AuditVerdict], out_path: Path) -> None:
        raise NotImplementedError("Phase 5: implement CSV verdict export.")

    def write_leaderboard(
        self, leaderboard: IntegrityLeaderboard, out_path: Path
    ) -> None:
        raise NotImplementedError("Phase 5: implement CSV leaderboard export.")

    def write_comparison(self, report: ComparisonReport, out_path: Path) -> None:
        raise NotImplementedError("Phase 5: implement CSV comparison export.")
