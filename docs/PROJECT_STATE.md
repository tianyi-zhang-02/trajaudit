# Project State

*Last updated: 2026-05-27, by Claude Code session at commit `a066d44` (this branch's base; see "Active work" for PR #1).*

## Identity

TrajAudit is a CLI stress-test runner for AI safety monitors. Given a corpus of labelled agent trajectories (currently MALT's public split), it applies a small battery of structural transformations to each trajectory, runs the chosen monitor on every variant, and reports per-transformation degradation in monitor performance (AUROC, Δ AUROC vs. clean, FPR shift at a calibrated threshold, worst-case Δ). v0.1 ships one monitor (METR's published MALT reward-hacking prompt) and three structural transformations (drop reasoning, truncate tail, pad with noop tool calls). No version is tagged yet; the v0.1 implementation lives in PR #1 awaiting one open decision before merge.

## Current phase

**Between Phase 0 (scaffold, on `main`) and v0.1 (in PR #1).** v0.1 implementation is feature-complete; one pre-merge fix (M1) is paused pending a strict-vs-lenient call from Tianyi.

## Active work

- **PR #1** — `v01-cli-stress-test-runner` branch, 18 commits ahead of `main`. v0.1 MALT adapter, three structural transformations, Monitor protocol + METRPromptMonitor, CLI `run` command, report card, integration attempt, schema fixes, pre-merge cleanup. **Owner: Tianyi** (review + decision on M1 validator semantics).
- **This branch (`claude/project-memory-setup`)** — project-memory infrastructure (PROJECT_STATE.md, COLLAB_CONTEXT.md, SESSION_PROTOCOLS.md, plus pointers in followups.md and README.md). Docs-only, no code touched. **Owner: Claude Code sandbox** (in progress, this commit).

## Open decisions

- **M1 fix authorization — strict vs. lenient `ScoreRecord` validator** (tracked in `docs/auto_session_questions.md` on PR #1; not yet on main). Root cause is case (a) type-level impossibility; proposed fix is a `__post_init__` validator on `ScoreRecord`. Pending Tianyi's call.
- **Q5 — Anthropic auth for the v0.1 live integration run** (same tracker). Sandbox `ANTHROPIC_API_KEY` is empty; live run requires Tianyi to run locally with a real key.

## Active blockers

- **PR #1 final commit** — blocked on M1 strict-vs-lenient decision (~10 min decision, ~15 min implementation). Owner: Tianyi.
- **v0.1 live integration evidence** (`docs/v01_first_run.md` numbers) — blocked on Q5 sandbox auth. Owner: Tianyi local task; not solvable inside Claude Code.

## Recently completed (last 30 days)

- **v0.1 implementation, in flight (PR #1)** — MALT adapter with on-disk-schema fixes, three structural transformations, Monitor protocol + METRPromptMonitor, CLI runner, report card with bootstrap CIs, four-doc supersession pass, tracker reorganization.
- **`a066d44 docs(pivot): add pivot decision recommendation`** — recommended reformulated (D) over (A-prime); confidence medium.
- **`9677191 docs(malt): add empirical recon notebook and summary`** — 28-cell notebook; HF blocker documented.
- **`04f7e90 docs(reading): add primary-source reading notes`** — Griffin et al., Radharapu et al., METR MALT, debate-literature follow-ups; key finding that Griffin already occupies the (A-prime) space.
- **`146aa3b docs: add repo audit, refactor summary, and followups`** — Phase 0 structural audit + Trajectory event-stream refactor summary.

## What's NOT in this project (anti-scope)

- **Semantic transformations** (CoT vague-ification, summarisation). v0.2.
- **Additional monitors** (EvilGenie monitor, cascaded multi-tier monitor, Qwen/OpenAI local monitors). v0.2+.
- **Additional benchmark adapters** (SWE-bench, Terminal-Bench, WebArena, GAIA). v0.2+.
- **Layer 1 sandbox / Layer 2 syntactic scanner.** Pre-pivot scope; abandoned. The pre-pivot multi-layer framework docs (`architecture.md`, `exploit-taxonomy.md`, `related-work.md`, `examples/README.md`) are marked SUPERSEDED in PR #1.
- **Paper writeup.** Deferred until v0.2 empirical results inform workshop-vs-conference scope.

## Pointers

- `README.md` — user-facing entry point (pre-pivot copy currently on `main`; v0.1 rewrite lives in PR #1).
- `docs/spec.md` — canonical v0.1 technical spec (in PR #1; not yet on `main`).
- `docs/followups.md` — non-blocking ideas and v0.2+ candidates.
- `docs/auto_session_questions.md` — current open questions for human review (in PR #1).
- `docs/COLLAB_CONTEXT.md` — collaboration context for AI agents working across sessions.
- `docs/SESSION_PROTOCOLS.md` — start-of-session / end-of-session protocols.
- `docs/pivot_decision.md` — the recommendation that defined v0.1's scope.
- `docs/reading_notes.md` — primary-source notes underpinning the pivot.
