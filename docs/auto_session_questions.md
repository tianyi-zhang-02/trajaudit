# Auto-session questions

Per Standing Rule 10. Items here need a human call before the relevant
session work can proceed. Reorganized into Open / Resolved / Abandoned
during the pre-merge cleanup pass on PR #1 (2026-05-27).

## Open

- **Q5 — Phase 3 live monitor calls blocked on Anthropic auth.** Raised
  during the v0.1 implementation session (Phase 3). Blocks the live
  end-to-end integration run that would produce real AUROC numbers for
  `docs/v01_first_run.md`. The sandbox env exposes `ANTHROPIC_API_KEY`
  with an empty-string value plus `ANTHROPIC_BASE_URL` pointing at a
  managed proxy whose auth is session-scoped and not visible to the
  Anthropic SDK. Per Standing Rules 5/6/7 I do not attempt to source a
  key from anywhere else. Unblock options (full detail in
  `docs/v01_first_run.md`):
  1. Run locally outside Claude Code with a real `ANTHROPIC_API_KEY`
     and `ANTHROPIC_BASE_URL` unset (~$2-3 expected spend).
  2. Expose a usable proxy token to the sandbox.
  3. Defer Phase 3 to a follow-up session; merge v0.1 without the
     live numbers.

  User has indicated Q5 is their local task; recommendation stands at
  option 1 for v0.1.0 evidence, option 3 for getting PR #1 merged
  without further delay.

## Resolved

- **Q1 — Branch name mismatch (`v01-cli-stress-test-runner` vs.
  `claude/v0.1-implementation`).** → Resolved by user direction in the
  autonomous-session safeguards turn ("Q1 — branch name. Accept the
  existing branch."). No commit needed; convention applies to future
  branches only.

- **Q2 — Four new runtime dependencies promoted in commit `497785b`.**
  → Resolved by commit `9524f50` (`chore(deps): move anthropic back to
  [llm] extra (Q2 follow-up)`), per user direction to accept
  `datasets` / `rich` / `scikit-learn` / `numpy` as runtime but move
  `anthropic` back under the `[llm]` extra with a guarded import.

- **Q3 — `.gitignore` modification in commit `497785b`.** → Resolved
  by user direction ("Q3 — .gitignore additions. Accept, no action.").
  No commit needed; the additions stand.

- **Q4 — Token-count guardrail hardcodes 200K context window for
  `claude-sonnet-4-7`.** → Resolved by commit `02c47f9`
  (`chore(monitors): add TODO for hardcoded context window (Q4)`), per
  user direction to accept the constant for v0.1 and add a TODO for
  parameterization in v0.2.

- **M1 — `ScoreRecord` length-mismatch hazard in `compute_report`.**
  → Resolved by commit `ce2d923` (`fix(report): enforce ScoreRecord
  invariant at construction (M1)`), per user authorisation of the
  strict `__post_init__` validator enforcing
  `(monitor_score is None) ⟺ (abstain == True)`. Full root-cause
  investigation in `docs/status_report.md` under "M1 root-cause
  investigation."

## Abandoned

(No items currently classified as abandoned.)
