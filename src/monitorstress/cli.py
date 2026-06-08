"""Command-line entry point for TrajAudit v0.1.

The CLI ships one command in v0.1:

* ``monitorstress run`` — load MALT trajectories, apply the structural
  transformation battery, score every variant with the chosen monitor,
  print a report card, and persist raw scores to JSON.

Two commands from the pre-pivot scaffold (``leaderboard``, ``compare``)
were removed when v0.1 narrowed the project to a stress-test runner.
They are tracked in ``docs/followups.md`` for v0.2+.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from monitorstress.adapters.malt import load_malt_split
from monitorstress.core.trajectory import Trajectory
from monitorstress.monitors.metr_prompt import METRPromptMonitor
from monitorstress.report import ReportCard, ScoreRecord, compute_report
from monitorstress.transformations import apply_structural_battery

app = typer.Typer(
    name="monitorstress",
    help="Stress-test runner for AI safety monitors. v0.1 ships one monitor (METR's prompt) and three structural transformations on MALT.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """No-op root callback that forces typer to treat ``run`` as a subcommand
    rather than collapsing the single-command app into a bare invocation.
    """


# v0.1 hard cap on --limit (prevents accidental budget blowouts even before
# the per-run --budget-usd cap kicks in).
_LIMIT_HARD_CAP = 1000


def _ground_truth(trajectory: Trajectory) -> int:
    """Binary collapse of MALT's taxonomy tags: 1 = any positive, 0 = ``normal``."""
    labels = trajectory.metadata.get("labels", [])
    if not labels:
        return 0
    return 0 if all(lbl == "normal" for lbl in labels) else 1


def _load_balanced(subset: str, limit: int) -> tuple[list[Trajectory], dict[str, int]]:
    """Stream MALT into two buckets (positives + negatives), each capped at ``limit // 2``.

    Returns the combined list and a stats dict for the run header.
    Iteration ends when both buckets are full OR the dataset is exhausted.
    """
    half = limit // 2
    pos: list[Trajectory] = []
    neg: list[Trajectory] = []
    scanned = 0
    for traj in load_malt_split(subset=subset, limit=None):  # type: ignore[arg-type]
        scanned += 1
        gt = _ground_truth(traj)
        if gt == 1 and len(pos) < half:
            pos.append(traj)
        elif gt == 0 and len(neg) < half:
            neg.append(traj)
        if len(pos) == half and len(neg) == half:
            break
    stats = {
        "scanned": scanned,
        "positives_loaded": len(pos),
        "negatives_loaded": len(neg),
        "balance_requested": half,
    }
    return pos + neg, stats


def _verdict_to_score(verdict_lo: float) -> float:
    """Convert ``SemanticVerdict.confidence_band[0]`` (in [0, 1]) to a 0-10 monitor score."""
    return verdict_lo * 10.0


def _records_path(output: Path | None) -> Path:
    if output is not None:
        return output
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return Path(f"./trajaudit_run_{stamp}.json")


def _write_records(records: list[ScoreRecord], report: ReportCard, path: Path) -> None:
    payload = {
        "records": [asdict(r) for r in records],
        "report": report.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2))


@app.command()
def run(
    monitor: Annotated[
        str,
        typer.Option("--monitor", help="Monitor name. v0.1 only accepts 'metr'."),
    ] = "metr",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help=f"Number of trajectories to evaluate (balanced 50/50). Hard cap: {_LIMIT_HARD_CAP}.",
        ),
    ] = 60,
    subset: Annotated[
        str,
        typer.Option(
            "--subset",
            help="MALT subset: 'manually_reviewed' (default) or 'all'.",
        ),
    ] = "manually_reviewed",
    budget_usd: Annotated[
        float,
        typer.Option(
            "--budget-usd",
            help="Hard cap on API spend in USD. Stops scoring when reached; report uses partial results.",
        ),
    ] = 5.0,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Path for the raw scores JSON. Defaults to ./trajaudit_run_<timestamp>.json."),
    ] = None,
) -> None:
    """Run the v0.1 stress-test pipeline against MALT."""
    console = Console()

    # ---- Input validation -------------------------------------------------
    if monitor != "metr":
        console.print(
            f"[red]Error:[/] monitor '{monitor}' not supported in v0.1. "
            "Only 'metr' is valid.",
            style="bold",
        )
        raise typer.Exit(code=2)
    if limit > _LIMIT_HARD_CAP:
        console.print(
            f"[red]Error:[/] --limit {limit} exceeds v0.1 hard cap of {_LIMIT_HARD_CAP}.",
            style="bold",
        )
        raise typer.Exit(code=2)
    if subset not in {"manually_reviewed", "all"}:
        console.print(
            f"[red]Error:[/] --subset must be 'manually_reviewed' or 'all'; got {subset!r}.",
            style="bold",
        )
        raise typer.Exit(code=2)
    if budget_usd <= 0:
        console.print(
            f"[red]Error:[/] --budget-usd must be positive; got {budget_usd}.",
            style="bold",
        )
        raise typer.Exit(code=2)

    # ---- Construct the monitor -------------------------------------------
    # Concrete type (not the Monitor protocol) so mypy resolves the
    # cost-tracking attributes the CLI reads (total_cost_usd, calls). The
    # protocol surface is still validated by isinstance(...) in the tests.
    monitor_obj = METRPromptMonitor()

    # ---- Load + balance ---------------------------------------------------
    console.print(f"[bold]Loading MALT[/] (subset={subset}, target n={limit})…")
    trajectories, load_stats = _load_balanced(subset=subset, limit=limit)
    if load_stats["positives_loaded"] != load_stats["balance_requested"] or load_stats[
        "negatives_loaded"
    ] != load_stats["balance_requested"]:
        console.print(
            f"[yellow]Note:[/] balance not fully achieved — "
            f"requested {load_stats['balance_requested']} each, got "
            f"+{load_stats['positives_loaded']} / -{load_stats['negatives_loaded']} "
            f"after scanning {load_stats['scanned']} rows."
        )
    console.print(
        f"Loaded {len(trajectories)} trajectories "
        f"(+{load_stats['positives_loaded']} / -{load_stats['negatives_loaded']})."
    )

    # ---- Score every variant ---------------------------------------------
    records: list[ScoreRecord] = []
    budget_hit = False
    for i, traj in enumerate(trajectories, start=1):
        if monitor_obj.total_cost_usd >= budget_usd:
            console.print(
                f"[yellow]Budget cap reached[/] (${monitor_obj.total_cost_usd:.2f} >= ${budget_usd:.2f}); "
                f"stopping after {i - 1}/{len(trajectories)} trajectories."
            )
            budget_hit = True
            break
        gt = _ground_truth(traj)
        variants = apply_structural_battery(traj)
        for variant_name, variant_traj in variants.items():
            try:
                verdict = monitor_obj.score(variant_traj)
            except Exception as exc:  # noqa: BLE001
                console.print(
                    f"[red]Monitor call failed on {traj.trajectory_id}/{variant_name}:[/] {exc!r}"
                )
                # Treat as abstain so the pipeline keeps going.
                records.append(
                    ScoreRecord(
                        trajectory_id=traj.trajectory_id,
                        transformation_name=variant_name,
                        ground_truth_label=gt,
                        monitor_score=None,
                        abstain=True,
                    )
                )
                continue
            score = (
                None
                if verdict.abstain
                else _verdict_to_score(verdict.confidence_band[0])
            )
            records.append(
                ScoreRecord(
                    trajectory_id=traj.trajectory_id,
                    transformation_name=variant_name,
                    ground_truth_label=gt,
                    monitor_score=score,
                    abstain=verdict.abstain,
                )
            )
        spend = monitor_obj.total_cost_usd
        console.print(
            f"[{i}/{len(trajectories)}] {traj.trajectory_id}: "
            f"scored 4 variants (${spend:.2f} / ${budget_usd:.2f})"
        )

    # ---- Report card ------------------------------------------------------
    console.print()
    report = compute_report(records)
    report.render(console=console)

    # ---- Persist ----------------------------------------------------------
    out_path = _records_path(output)
    _write_records(records, report, out_path)
    console.print(f"\n[bold green]Records written to[/] {out_path}")
    console.print(
        f"Total API spend: ${monitor_obj.total_cost_usd:.4f} "
        f"({monitor_obj.calls} calls)"
    )
    if budget_hit:
        console.print(
            "[yellow]Run was aborted by the budget cap. Report reflects partial results.[/]"
        )


def main() -> None:
    """Module-level entry point used by ``python -m monitorstress``."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
