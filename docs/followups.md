# Followups

Out-of-scope items noticed during the post-audit refactor (commits
9aa2160 → 25839b1). None block Phase 1.

## Schema

- **`HarnessResult` vs. `ScoringEvent` overlap.** `Trajectory` has a
  top-level `harness_result: HarnessResult | None` and the event stream
  can now carry `ScoringEvent`s. Adapters could be made to emit a
  closing `ScoringEvent` instead, with `harness_result` becoming a
  derived convenience property. Reconcile in Phase 1 once at least one
  adapter is real.
- **Sunset date for deprecated `Step` / `StepType` / `FileEdit` /
  `ShellCommand`.** Currently labelled "one release cycle." Pick a
  concrete version (e.g. drop in 0.2.0) before the first release.
- **Typed metadata on events.** `ToolCallEvent.metadata`,
  `ObservationEvent.metadata`, `ReasoningEvent.metadata` are
  `dict[str, Any]`. For known fields (e.g. token usage, latency), a
  typed sidecar would catch typos. Worth doing only after a real
  adapter shows what fields recur.
- **`escalated_from: str | None` could be an enum.** Once the provider
  list is stable (vllm-qwen2.5-7b, anthropic-claude-opus, …), promote
  to a `ProviderTier` StrEnum the same way `TaxonomyTag` was promoted.

## Validation

- **Composition policy spec.** `AuditVerdict.compose` is still a
  `NotImplementedError` with the policy described only in the
  docstring. Worth a dedicated design doc + unit tests before Phase 5,
  especially around the `UNCERTAIN` ↔ `SUSPECT` boundary.
- **`ToolCallEvent.arguments` default.** Currently required. If real
  adapters routinely pass `arguments={}`, switch to
  `Field(default_factory=dict)` for ergonomics.
- **Round-trip via `model_dump()` (not just JSON).** Current tests
  cover JSON round-trip. Adding a `model_dump()` / `model_validate()`
  test would catch Python-side discriminator mishandling, separately
  from JSON serialization.

## Docs

- **`docs/pivot_review.md` is referenced but missing.** The refactor
  prompt pointed at it for context; the inline summary was enough this
  time, but the file should exist so it can be referenced again.
- **Update `docs/architecture.md` to reflect the unified event stream.**
  The architecture doc may still describe the three-list shape. Audit
  on next docs pass.
- **Migration example in CHANGELOG / release notes** when 0.1.0 lands —
  the old-vs-new snippet in `refactor_summary.md` is reusable.

## Tooling

- **Phantom-dep import test.** A small test that imports each
  `optional-dependencies` group's modules under conditional skips
  would catch the next round of phantom deps automatically.
- **CI matrix is `[3.11, 3.12]` only.** Add 3.13 once it's broadly
  available in `setup-python@v5`.

## v0.1 follow-ups (added during Tasks 4 + 5)

- **`leaderboard` + `compare` CLI commands removed.** The pre-pivot
  `cli.py` had stub subcommands for both. Removed in commit
  `feat(cli): add trajaudit run command` to narrow v0.1 to a single
  command. Reinstate when v0.2 reporting work is ready — the data
  shape (`ReportCard`, `ScoreRecord`) is already friendly to both.
- **Version bump from `0.0.1` to `0.1.0`.** Defers to the user because
  it touches `pyproject.toml`'s `[project]` metadata block, which
  the autonomous-session safeguards exclude.
- **Multi-monitor support.** `--monitor` accepts only `"metr"` in
  v0.1. Generalize once a second concrete monitor exists (EvilGenie
  is the natural first follow-on).
- **Per-tag AUROC + calibration curves.** Explicitly excluded from
  v0.1's report card. Likely homes: a sibling `report` function or
  a `--report-detail` CLI flag.
- **Context-window parameterization.** `METRPromptMonitor` hardcodes
  `_DEFAULT_CONTEXT_WINDOW = 200_000`. TODO comment in place;
  parameterize per-model when v0.2 introduces additional monitor
  families.
- **Cost-tracking placement.** `Monitor` instances expose
  `total_cost_usd` / `total_input_tokens` / `total_output_tokens` /
  `calls` as instance attributes. Works for v0.1 with one monitor; if
  multiple monitors are composed in v0.2, consider a shared
  `CostTracker` injected at construction or returned alongside the
  verdict via a richer return type.
- **Pricing constants.** `_INPUT_USD_PER_MTOK = 3.0` and
  `_OUTPUT_USD_PER_MTOK = 15.0` are hardcoded for `claude-sonnet-4-7`
  in `metr_prompt.py`. If Anthropic adjusts Sonnet pricing or v0.2
  adds non-Anthropic monitors, externalize.
- **`load_malt_split` only knows `metr-evals/malt-public`.** A second
  variant for the DAG-format `malt-transcripts-public` would let us
  cover the multi-completion case the current adapter flattens.
