# TrajAudit v0.1 specification — as built

This is the canonical record of what v0.1 of TrajAudit actually ships,
written *after* implementation rather than before. If anything else in the
repo's documentation disagrees with this file, this file is authoritative
for the v0.1 surface; conflicts should be resolved by editing the other
doc to match.

## What v0.1 is

A CLI stress-test runner for AI safety monitors. Given a corpus of agent
trajectories with ground-truth labels, TrajAudit:

1. Applies three structural transformations to each trajectory (drop the
   reasoning, truncate the end, pad with noop tool calls).
2. Scores every variant (clean + 3 transformations) with the chosen
   monitor.
3. Reports per-transformation AUROC, Δ AUROC vs. clean, FPR shift at a
   clean-calibrated 5% FPR threshold, and a worst-case-degradation
   summary.

The whole pipeline runs as a single CLI invocation:

```
trajaudit run --monitor metr --limit 60 --budget-usd 5.00
```

## What v0.1 ships

| Surface | Module | Notes |
|---|---|---|
| Trajectory event-stream model | `trajaudit.core.events` + `trajaudit.core.trajectory` | Pre-existed; unchanged by v0.1. |
| Verdict + taxonomy | `trajaudit.core.verdict` | Pre-existed; unchanged by v0.1. |
| MALT adapter | `trajaudit.adapters.malt` | `load_malt_split()`, `malt_row_to_trajectory()`. Requires `HF_TOKEN`. |
| Structural transformations | `trajaudit.transformations.structural` | `drop_reasoning`, `truncate_observations`, `pad_with_noops`, `apply_structural_battery`. Pure functions. |
| Monitor protocol | `trajaudit.monitors.Monitor` | Runtime-checkable Protocol. `name: str` + `score(Trajectory) -> SemanticVerdict`. |
| METR monitor | `trajaudit.monitors.metr_prompt.METRPromptMonitor` | Verbatim METR MALT reward-hacking prompt; calls `claude-haiku-4-5-20251001`. |
| Report card | `trajaudit.report` | `compute_report()`, `ScoreRecord`, `ReportCard`, `TransformReport`. |
| CLI | `trajaudit.cli` | Single command: `trajaudit run`. |

## What v0.1 does NOT ship

Explicit non-scope, deferred to v0.2+:

- **Semantic transformations.** No CoT vague-ification, no
  summarization. Structural-only.
- **Additional monitors.** No EvilGenie monitor, no cascaded multi-tier
  monitor, no Qwen/OpenAI/etc. The protocol surface is in place so
  these are PR-sized additions.
- **Additional benchmark adapters.** MALT only; no SWE-bench / Terminal-Bench
  / WebArena / GAIA.
- **Layer 1 sandbox.** No Docker replay, no filesystem diff.
- **Layer 2 syntactic scanner.** No AST detection of exploit patterns.
- **Leaderboard / `compare` CLI commands.** Removed in the Task 4 rewrite
  of `cli.py` (`feat(cli): add trajaudit run command`). Tracked for
  v0.2+ in `docs/followups.md`.
- **Web UI of any kind.** CLI only.

## Public API surface

Only the names below are considered part of the v0.1 stable public API.
Anything else is private and may change without notice in 0.x.

```python
# Data model
from trajaudit.core.trajectory import Trajectory, HarnessResult
from trajaudit.core.events import (
    TrajectoryEvent, ReasoningEvent, ToolCallEvent, ObservationEvent, ScoringEvent,
)
from trajaudit.core.verdict import (
    SemanticVerdict, SemanticLabel, TaxonomyTag, IntegrityLabel, Severity,
    WorkspaceFinding, SyntacticFinding, AuditVerdict,
)

# Adapter
from trajaudit.adapters.malt import load_malt_split, malt_row_to_trajectory

# Transformations
from trajaudit.transformations import (
    drop_reasoning, truncate_observations, pad_with_noops, apply_structural_battery,
)

# Monitors
from trajaudit.monitors import Monitor, METRPromptMonitor

# Report
from trajaudit.report import (
    ScoreRecord, TransformReport, ReportCard, compute_report,
)
```

## CLI specification

```
trajaudit run [OPTIONS]
```

| Option | Default | Notes |
|---|---|---|
| `--monitor` | `metr` | Only `metr` valid in v0.1. Anything else exits with code 2. |
| `--limit` | `60` | Trajectories to evaluate. Loaded balanced 50/50 pos/neg if possible. Hard cap `1000`. |
| `--subset` | `manually_reviewed` | `manually_reviewed` or `all`. Passed through to the MALT loader. |
| `--budget-usd` | `5.0` | Hard cap on API spend. Pipeline aborts cleanly when reached, partial report. |
| `--output` | `./trajaudit_run_<UTC timestamp>.json` | Where the records + report JSON are written. |

### Exit codes

- `0` — clean completion (including budget-cap aborts; those are
  expected outcomes, not failures).
- `2` — input-validation error (unsupported monitor, over-cap limit,
  bad subset value, nonpositive budget).
- Any other non-zero — uncaught exception. The CLI does not currently
  swallow exceptions that bubble out of HF or the API beyond
  individual monitor-call failures.

### Required environment

- `HF_TOKEN` — required by the MALT adapter; the adapter raises a
  `RuntimeError` at first use if absent. The error message includes
  the exact setup steps (generate token + accept dataset terms).
- `ANTHROPIC_API_KEY` — required by `METRPromptMonitor` (read by the
  `anthropic` SDK).

## Deviations from the v0.1 prompt

Three deviations from the original prompt, all documented in their
commits and `docs/auto_session_questions.md`:

1. **Branch name.** Work landed on `v01-cli-stress-test-runner` rather
   than the prompt's preferred `claude/v0.1-implementation`. Accepted
   by the user (`docs/auto_session_questions.md` Q1).
2. **`anthropic` dependency placement.** Initially promoted from the
   `[llm]` extra to runtime; subsequently moved back to `[llm]` with
   a guarded import in `METRPromptMonitor` (commit `9524f50`).
3. **Context-window constant** for `claude-haiku-4-5-20251001` is hardcoded at
   200K with a TODO comment for parameterization in v0.2
   (commit `02c47f9`).

## Tests + lint state at v0.1 freeze

- 96 tests pass (1 smoke + 18 verdict/events + 15 adapter +
  27 transformations + 12 monitor + 15 report + 9 CLI). No live API or
  HF calls in tests; all external dependencies are mocked or
  fixture-driven.
- `ruff check .` clean across the full tree.
- `mypy src/trajaudit` clean across 38 source files.

## Outstanding items before v0.1.0 release tag

Tracked in `docs/followups.md`; pulled forward here for visibility:

- Live-MALT smoke test (Phase 3 of the v0.1 work plan). Not yet
  executed; depends on a working `HF_TOKEN` in the run environment.
- Version bump from `0.0.1` to `0.1.0` in `pyproject.toml`. Defers to
  the user because it touches the `[project]` metadata block (covered
  by the autonomous-session safeguards).
