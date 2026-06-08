# Followups

> Open follow-ups. See `docs/PROJECT_STATE.md` for canonical project state.

Out-of-scope items noticed across sessions, classified Open / Resolved /
Abandoned during the pre-merge cleanup pass on PR #1 (2026-05-27). None
of the Open items block PR #1 merge — they are v0.1.1 / v0.2+ work.

## Open

### Schema

- **`HarnessResult` vs. `ScoringEvent` overlap.** `Trajectory` has a
  top-level `harness_result: HarnessResult | None` and the event stream
  can now carry `ScoringEvent`s. Adapters could be made to emit a
  closing `ScoringEvent` instead, with `harness_result` becoming a
  derived convenience property. The MALT adapter currently emits both
  when a row carries scoring data — confirmed live in Phase 3.

- **Sunset date for deprecated `Step` / `StepType` / `FileEdit` /
  `ShellCommand`.** Currently labelled "one release cycle." Pick a
  concrete version (e.g., drop in 0.2.0) before the v0.1.0 tag.

- **Typed metadata on events.** `ToolCallEvent.metadata`,
  `ObservationEvent.metadata`, `ReasoningEvent.metadata` are
  `dict[str, Any]`. For known fields (e.g., token usage, latency,
  the `noop=True` flag the v0.1 `pad_with_noops` already emits), a
  typed sidecar would catch typos.

- **`escalated_from: str | None` could be an enum.** Once the provider
  list stabilises, promote to a `ProviderTier` StrEnum the same way
  `TaxonomyTag` was promoted.

### Validation

- **Composition policy spec.** `AuditVerdict.compose` is still a
  `NotImplementedError` with the policy described only in the
  docstring. Worth a dedicated design doc + unit tests before any
  AuditVerdict consumer ships.

- **`ToolCallEvent.arguments` default.** Currently required. Real
  MALT adapter does pass `arguments={}` for some `function_call`s
  with empty arguments — switching to `Field(default_factory=dict)`
  is justified by observed usage.

- **Round-trip via `model_dump()` (not just JSON).** Current tests
  cover JSON round-trip. Adding a `model_dump()` / `model_validate()`
  test would catch Python-side discriminator mishandling.

### Tooling

- **Phantom-dep import test.** A small test that imports each
  `optional-dependencies` group's modules under conditional skips
  would catch the next round of phantom deps automatically.

- **CI matrix is `[3.11, 3.12]` only.** Add 3.13 once it's broadly
  available in `setup-python@v5`.

### v0.1 implementation residue

- **`leaderboard` + `compare` CLI commands removed.** The pre-pivot
  `cli.py` had stub subcommands for both. Removed during the v0.1
  CLI rewrite to narrow to a single command. Reinstate when v0.2
  reporting work lands — the data shape (`ReportCard`, `ScoreRecord`)
  is already friendly to both.

- **Version bump from `0.0.1` to `0.1.0`.** Defers to the user
  because it touches `pyproject.toml`'s `[project]` metadata block,
  which the autonomous-session safeguards exclude.

- **Multi-monitor support.** `--monitor` accepts only `"metr"` in
  v0.1. Generalise once a second concrete monitor exists (EvilGenie
  is the natural first follow-on).

- **Per-tag AUROC + calibration curves.** Explicitly excluded from
  v0.1's report card. Likely homes: a sibling `report` function or
  a `--report-detail` CLI flag.

- **Context-window parameterisation.** `METRPromptMonitor` hardcodes
  `_DEFAULT_CONTEXT_WINDOW = 200_000`. TODO comment in place; parameterise
  per-model when v0.2 introduces additional monitor families.

- **Cost-tracking placement.** `Monitor` instances expose
  `total_cost_usd` / `total_input_tokens` / `total_output_tokens` /
  `calls` as instance attributes. Works for v0.1 with one monitor; if
  multiple monitors are composed in v0.2, consider a shared
  `CostTracker` injected at construction or returned alongside the
  verdict via a richer return type.

- **Pricing constants.** `_INPUT_USD_PER_MTOK = 1.0` and
  `_OUTPUT_USD_PER_MTOK = 5.0` are hardcoded for `claude-haiku-4-5-20251001`
  in `metr_prompt.py`. If Anthropic adjusts Haiku pricing or v0.2
  adds non-Anthropic monitors, externalise.

- **`load_malt_split` only knows `metr-evals/malt-public`.** A second
  variant for the DAG-format `malt-transcripts-public` would let us
  cover the multi-completion case the current adapter flattens.

- **Synthetic `[role:source] content` transcript format diverges from
  METR's chat-completion format.** `METRPromptMonitor._format_transcript`
  bakes events into a human-readable string rather than reconstructing
  the chat structure METR's monitor would have seen. Surfaced as L1 in
  `docs/status_report.md`. Likely affects live AUROC reproduction
  against METR's 0.96.

## Resolved

- **Update `docs/architecture.md` to reflect the unified event stream.**
  → Obviated by commit `46b5545` (`docs: mark four pre-pivot docs as
  superseded`). `architecture.md` is no longer the canonical
  architecture description; `docs/spec.md` is. The unified-event-stream
  story is documented in `docs/refactor_summary.md` and `docs/spec.md`.

## Abandoned

- **`docs/pivot_review.md` is referenced but missing.** Originally
  raised because the post-audit refactor prompt pointed at a doc that
  was never created. The pivot reasoning now lives in
  `docs/pivot_decision.md` and `docs/reading_notes.md`, which together
  cover the rationale a `pivot_review.md` would have held. No standalone
  doc needed.

- **Migration example in CHANGELOG / release notes when 0.1.0 lands.**
  Originally proposed reusing the old-vs-new snippet in
  `docs/refactor_summary.md`. The v0.1 release will publish against a
  fresh repo with no external consumers of the pre-pivot API; a
  migration guide would have no audience. The `refactor_summary.md`
  snippet stays in place as decision history rather than as user-facing
  migration material.
