"""Command-line entry point for TrajAudit.

The CLI is built on `typer`_ and is intentionally thin — the bulk of
the orchestration lives in :mod:`trajaudit.core.runner`. The CLI's job
is to parse arguments, configure the runner, and emit reports.

Subcommands:

* ``trajaudit run`` — audit a directory of trajectories for a given
  benchmark and emit :class:`~trajaudit.core.verdict.AuditVerdict` records.
* ``trajaudit leaderboard`` — aggregate verdicts into an
  integrity-adjusted leaderboard across many agents' runs.
* ``trajaudit compare`` — diff the integrity-adjusted ranking between
  two submissions on the same benchmark. The framework's headline UX.

.. _typer: https://typer.tiangolo.com/
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="trajaudit",
    help="Multi-layer audit framework for agent benchmark integrity.",
    no_args_is_help=True,
)


@app.command()
def run(
    benchmark: Annotated[
        str,
        typer.Option(
            "--benchmark",
            "-b",
            help="Benchmark identifier (e.g. 'swe-bench-verified', 'terminal-bench').",
        ),
    ],
    trajectory_dir: Annotated[
        Path,
        typer.Option(
            "--trajectory-dir",
            "-t",
            help="Directory containing agent trajectory artifacts to audit.",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional path to write the AuditVerdict report (JSON).",
        ),
    ] = None,
) -> None:
    """Audit every trajectory in ``trajectory_dir`` against ``benchmark``."""
    raise NotImplementedError("Phase 1: wire up runner + benchmark adapters.")


@app.command()
def leaderboard(
    runs_dir: Annotated[
        Path,
        typer.Option(
            "--runs-dir",
            "-r",
            help="Directory containing multiple agents' run subdirectories.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Destination file. Format inferred from extension (.md / .json / .csv).",
        ),
    ],
) -> None:
    """Build an integrity-adjusted leaderboard across agents under ``runs_dir``."""
    raise NotImplementedError("Phase 5: implement leaderboard aggregation.")


@app.command()
def compare(
    benchmark: Annotated[
        str,
        typer.Option(
            "--benchmark",
            "-b",
            help="Benchmark identifier the two submissions both target.",
        ),
    ],
    submission_a: Annotated[
        Path,
        typer.Option(
            "--submission-a",
            "-a",
            help="Path to submission A's trajectory directory or verdict file.",
        ),
    ],
    submission_b: Annotated[
        Path,
        typer.Option(
            "--submission-b",
            "-B",
            help="Path to submission B's trajectory directory or verdict file.",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional destination for the comparison report (defaults to stdout).",
        ),
    ] = None,
) -> None:
    """Diff the integrity-adjusted ranking between two submissions.

    Headline diagnostic: when submissions A and B have similar raw
    pass-rates but very different exploit counts, the rank diff makes
    the gap legible.
    """
    raise NotImplementedError("Phase 5: implement integrity-adjusted comparison.")


def main() -> None:
    """Module-level entry point used by ``python -m trajaudit``."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
