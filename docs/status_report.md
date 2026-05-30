# TrajAudit status report (PR #1 readiness review)

Read-only diagnostic, 2026-05-27. ~45 min of diff/doc review. Written to
inform the merge decision on
[PR #1](https://github.com/tianyi-zhang-02/trajaudit/pull/1). No code
or doc changes made during this pass.

## TL;DR (read this first)

**PR #1 is mergeable with ~30-45 min of pre-merge cleanup, not "ready to merge as-is."** Three new things this review surfaced that weren't in prior status messages:

- **M1 (medium):** `compute_report` in `report.py:238-269` can `IndexError` on `ScoreRecord(abstain=False, monitor_score=None)` — `clean_y` and `clean_s` are built with different filter predicates (`not r.abstain` vs `monitor_score is not None`). No test covers the combination.
- **Doc coherence:** four pre-pivot docs (`architecture.md`, `exploit-taxonomy.md`, `related-work.md`, `examples/README.md`) describe the multi-layer framework as if current. An outside reader who finds them before `spec.md` will conclude the README is wrong about what the tool does.
- **L1 reproduction caveat:** `METRPromptMonitor._format_transcript` emits a synthesized `[role:source] content` format, not METR's literal chat-completion format — live AUROC won't match METR's 0.96 even before sample noise. Undocumented today.

**Top action:** fix M1 (~10 lines + 1 test) and delete/stub the four stale docs. ~30-45 min, then merge.

## 1. Repo at a glance

| | |
|---|---|
| Branch | `v01-cli-stress-test-runner` |
| Last commit | `a6a398f docs: correct MALT row count (2690->1826) …` |
| Commits ahead of `origin/main` | **16** |
| Tests | **101** passing (1 smoke + 18 verdict/events + 20 adapter + 27 transformations + 12 monitor + 15 report + 9 CLI; ~12s wall) |
| Lint | `ruff check .` — clean |
| Type-check | `mypy src/trajaudit` — no issues, 38 files |
| Python LOC in `src/` | **3,371** |
| LOC in `tests/` | **1,542** |
| LOC in `docs/` | **2,092** |

Tests-to-source ratio 0.46 (decent for a scaffold; could be higher with
branch-coverage of report.py's bootstrap loops).

## 2. PR #1 summary

- **16 commits** on the branch.
- **33 files changed** vs `origin/main`.
- **+5,188 / -254** lines.

Per-commit (chronological), grouped by task:

**Task 1 — MALT adapter**
- `497785b feat(adapters): add MALT ingestion`

**Task 2 — Structural transformations**
- `ace6bd1 feat(transforms): add three structural transformations`

**Task 3 — Monitor protocol + METR**
- `91ce037 feat(monitors): add Monitor protocol and METR implementation`

**Autonomous-session housekeeping**
- `bcec528 docs(auto): flag branch-name mismatch and dep additions for review`
- `9524f50 chore(deps): move anthropic back to [llm] extra (Q2 follow-up)`
- `02c47f9 chore(monitors): add TODO for hardcoded context window (Q4)`

**Task 5 — Report card** *(landed before Task 4 because the CLI depends on it)*
- `5bba744 feat(report): add report card computation and rendering`

**Task 4 — CLI**
- `4f0a956 feat(cli): add trajaudit run command`

**v0.1 docs**
- `efc52d6 docs(v0.1): add spec.md, rewrite README, expand followups`

**Phase 3 fixes (surfaced by live MALT)**
- `ce25645 fix(adapters): fall back to HF cache token when HF_TOKEN unset`
- `c715cab fix(cli): drop redundant type-ignores on monitor cost-tracking access`
- `9658035 fix(adapters): use MALT's actual split name 'public', not 'train'`
- `2d6d8cf fix(adapters): handle MALT's real on-disk row schema`
- `8532cc1 fix(adapters): apply row.metadata routing to manually_reviewed filter too`

**Integration documentation + correction**
- `2096a80 docs(integration): document Phase 3 partial run + Anthropic auth blocker`
- `a6a398f docs: correct MALT row count (2690->1826) and document real schema`

## 3. What v0.1 actually delivers

| Capability | Status | Evidence |
|---|---|---|
| MALT ingestion — fixture-driven | **working** | `tests/adapters/test_malt.py` (20 tests, including 5 against `real_shape_openai_function_call.json`) |
| MALT ingestion — live HF download + load + filter | **working** (verified end-to-end in Phase 3, loaded 20 manually-reviewed trajectories balanced 10/10) | manual run via `trajaudit run …` |
| `drop_reasoning` transformation | **working** | `tests/transformations/test_drop_reasoning.py` (7 tests) |
| `truncate_observations` transformation | **working** | `tests/transformations/test_truncate_observations.py` (9 tests) |
| `pad_with_noops` transformation | **working** | `tests/transformations/test_pad_with_noops.py` (11 tests) |
| `apply_structural_battery` | **working** | `tests/transformations/test_pad_with_noops.py::test_apply_structural_battery_returns_four_variants` |
| `Monitor` protocol | **working** (runtime-checkable; `isinstance(m, Monitor)` works) | `tests/monitors/test_metr_prompt.py::test_metr_monitor_satisfies_protocol` |
| `METRPromptMonitor` — score/abstain/retry/cost-tracking | **working** (against mocked Anthropic client) | `tests/monitors/test_metr_prompt.py` (12 tests) |
| `METRPromptMonitor` — live API call | **not validated** | Blocked on sandbox auth — see Q5 / `docs/v01_first_run.md` |
| `trajaudit run` CLI — flags + validation + JSON output | **working** (hermetic) | `tests/test_cli.py` (9 tests) |
| Report card — AUROC + bootstrap CI + Δ AUROC + FPR shift + Rich render | **working** (against synthetic records) | `tests/test_report.py` (15 tests) |
| End-to-end pipeline (MALT → transformations → monitor → report) | **partial** — orchestration works, abstain path handles all failure modes; live API never executed because of auth blocker | Phase 3 log in `docs/v01_first_run.md` |

## 4. What's NOT in v0.1

Explicitly out of scope per `docs/spec.md`:

- **Semantic transformations** (CoT vague-ification, summarize). v0.2.
- **EvilGenie monitor.** v0.2.
- **Cascaded multi-tier monitor.** v1.1.
- **OpenAI / Qwen / open-weight monitor backends.** v0.2.
- **Additional benchmark adapters** (SWE-bench, Terminal-Bench, WebArena, GAIA, OSWorld). v0.2+.
- **Layer 1 sandbox** (Docker replay, FS diff). The pre-pivot Phase 3 plan.
- **Layer 2 syntactic scanner.** The pre-pivot Phase 2 plan.
- **`leaderboard` / `compare` CLI subcommands.** Removed in `feat(cli)`; tracked in `docs/followups.md` under "v0.1 follow-ups."
- **Per-tag AUROC, calibration curves, additional metrics on the report card.** Tracked in `docs/followups.md`.
- **Paper-shaped artifacts.** No writeup, no benchmark-style leaderboard.

Items previously flagged but not yet addressed (cross-references):

- `docs/auto_session_questions.md` Q5 — live API integration blocker.
- `docs/followups.md` v0.1 section — version bump to 0.1.0 (touches governance file); multi-monitor support; cost-tracking placement; pricing-constant externalization; DAG-format MALT adapter.
- `docs/auto_session_questions.md` Q4 — hardcoded 200K context window.

## 5. Risks before merge

Ordered by severity. ~45 minutes of diff review.

### M1 — `compute_report` length-mismatch hazard *(medium)*

`src/trajaudit/report.py:238-269`. The clean baseline builds two parallel
numpy arrays:

```python
clean_records = [r for r in by_transform.get("clean", []) if not r.abstain]
clean_y = np.array([r.ground_truth_label for r in clean_records], dtype=int)
clean_s = np.array(
    [r.monitor_score for r in clean_records if r.monitor_score is not None],
    dtype=float,
)
```

`clean_y` is keyed by `not r.abstain`; `clean_s` is keyed by
`monitor_score is not None`. These are *independent* fields on
`ScoreRecord` (`abstain: bool = False`, `monitor_score: float | None`).
The CLI happens to set them together, but a user constructing
`ScoreRecord(abstain=False, monitor_score=None)` would slip records into
`clean_y` without a matching entry in `clean_s`. The bootstrap loop
(`idx = rng.integers(0, len(clean_y), size=len(clean_y))`) would then
hit `clean_s[idx]` → `IndexError`. Same hazard on `_threshold_at_fpr`
(`y_score[y_true == 0]` with mismatched lengths) and the per-transform
branch on lines 308-316. **Fix:** filter `clean_records` by both
predicates, or assert at the top of the function. No test currently
covers this combination.

### M1 root-cause investigation

Producers of `ScoreRecord` in the codebase:

| Site | Construction shape | Invariant maintained? |
|---|---|---|
| `src/trajaudit/cli.py:212-220` (monitor exception path) | `monitor_score=None, abstain=True` | ✓ |
| `src/trajaudit/cli.py:227-235` (verdict path) | `score = None if verdict.abstain else _verdict_to_score(...)`, `abstain=verdict.abstain` | ✓ |
| `tests/test_report.py:59` (`_make_records` helper) | always numeric `score`, `abstain=False` | ✓ |
| `tests/test_report.py:190` (abstain test) | `monitor_score=None, abstain=True` | ✓ |
| `tests/test_report.py:207` (all-abstain test) | `monitor_score=None, abstain=True` | ✓ |
| `tests/test_report.py:273` (single-class test) | `monitor_score=0.9` (default `abstain=False`) | ✓ |

In `cli.py:222-226` the score assignment is:

```python
score = None if verdict.abstain else _verdict_to_score(verdict.confidence_band[0])
```

`_verdict_to_score(verdict.confidence_band[0])` returns a non-None float
unconditionally (`return verdict_lo * 10.0`), and
`SemanticVerdict.confidence_band[0]` is constrained to `[0.0, 1.0]` by
the verdict's own validator. So `score is None ⟺ verdict.abstain` at
the CLI emission site, and `abstain` propagates from `verdict.abstain`
on the same line.

**Conclusion: this is case (a) — type-level impossibility.** The
implicit invariant `(monitor_score is None) ⟺ (abstain == True)` is
maintained by every current producer but is not enforced at the type
level on `ScoreRecord`. The renderer's failure mode is dormant today;
it would trigger on the first producer (a future monitor wrapper, a
notebook script, an EvilGenie monitor in v0.2) that violated the
invariant, possibly silently — `IndexError` is the visible symptom
but the underlying bug would be a producer-side semantics violation.

**Proposed fix (NOT YET IMPLEMENTED, awaiting your go-ahead per the
prompt's stop-and-report on case (a)):**

1. Add `__post_init__` to `ScoreRecord` (which is currently a plain
   `@dataclass`) enforcing the biconditional and a clear `ValueError`
   on violation, e.g.:
   ```python
   def __post_init__(self) -> None:
       if self.abstain and self.monitor_score is not None:
           raise ValueError(
               f"ScoreRecord: abstain=True requires monitor_score is None; "
               f"got monitor_score={self.monitor_score!r}"
           )
       if not self.abstain and self.monitor_score is None:
           raise ValueError(
               "ScoreRecord: monitor_score is None requires abstain=True"
           )
   ```
2. Add one regression test exercising the failing case (would now
   raise `ValueError` before reaching `compute_report`).
3. Add one positive test verifying the valid combinations
   (`abstain=True ∧ score=None` and `abstain=False ∧ score=0.5`) both
   construct successfully.

**Blast-radius assessment.** Despite the prompt's note that case (a)
fixes "potentially have a wider blast radius," the actual radius here
is small because every current producer already complies with the
invariant — no producer code needs to change, no test needs to be
rewritten. Mypy would not flag anything (the validator runs at
construction time, not annotation time). The change is a single
`__post_init__` method on one dataclass plus two new tests.

**One question for you to weigh in on before I implement:**

Should the validator be strict or lenient? Strict (proposed above) is
the natural choice for v0.1 — fail fast on producers that violate the
invariant. Lenient (treat `(abstain=False, monitor_score=None)` as
"no signal, drop from numeric computation") is the alternative if you
expect future producers to legitimately emit records with no score
and no abstain semantics (e.g., a monitor that errored at the network
level but you don't want to commit to the abstention semantics). My
recommendation is strict, but I'll defer.

### L1 — Synthetic transcript format diverges from METR's *(low, but reproduction-affecting)*

`src/trajaudit/monitors/metr_prompt.py:99-114`. `_format_transcript` emits

```
[Task description]
benchmark=malt-public task_id=…

[Transcript]
[reasoning] …
[tool_call:bash] {'cmd': 'ls'}
[observation:stdout] file1 file2
```

METR's monitors run on the agent's original chat-completion format (the
prompt template's `[Task description and transcript chunks inserted
here]` placeholder is filled with the agent's literal messages). Our
synthesized format is shorter, normalized, and labels-prefixed in a way
the original isn't. **Consequence:** if the live integration ever runs,
AUROC won't match METR's published numbers even before sample noise —
not because of a bug but because of input distribution shift. Worth
noting in `docs/spec.md` deviations and `docs/malt_recon.md`'s
reproduction-caveat section.

### L2 — `malt_row_to_trajectory` falsy-value fall-through *(low)*

`src/trajaudit/adapters/malt.py:339-341`. The `_md(...) or _md(...) or ...
or "unknown"` chain for `transcript_id` falls through on any falsy value
(`0`, `""`, `False`). If MALT ever ships `run_id=0` or a task_id that's
the empty string, the synthesized call-id namespace silently collapses
to `"unknown-…"` for an entire row, breaking call_id uniqueness. Use
`x if x is not None else y` instead. Not currently triggered by any
fixture or by the real MALT rows I inspected (run_ids were ≥ 112337).

### L3 — `_events_from_messages` mis-classifies sequential user messages *(low)*

`src/trajaudit/adapters/malt.py:199-205`. The framing-skip logic only
fires once. A second consecutive `role="user"` message before any
assistant turn is emitted as `ObservationEvent(source="stdout")`. Real
agent traces rarely produce this pattern, but it's incorrect: a second
user message is typically a clarification or extended task, not an
observation. Won't crash; just produces semantically muddy events.

### L4 — `paired_calls` silently drops orphan observations *(low)*

`src/trajaudit/core/trajectory.py` (pre-existing). When an
`ObservationEvent` has no matching `ToolCallEvent` by `call_id`,
`paired_calls()` yields nothing for it. Documented in the function's
docstring as "first observation matching a given call_id wins," but the
*opposite* case (orphan observation) isn't tested or even documented.
Pre-existing; not introduced by this PR.

### L5 — `variants["clean"]` is the literal input trajectory *(low)*

`src/trajaudit/transformations/structural.py:158`. `apply_structural_battery`
returns the original Trajectory object as the `"clean"` variant. A
caller that mutates `variants["clean"]` mutates their input. This is
tested by `test_apply_structural_battery_returns_four_variants` (which
asserts `variants["clean"] is sample_trajectory`) but not documented in
the function's own docstring. Pydantic models are largely immutable in
practice (`model_copy` is the mutation primitive), so this is more a
"polish item" than a bug.

### I1 — Empty-trajectory run renders an empty report table *(info / UX)*

When 0 trajectories load (as in the first three Phase 3 runs), the CLI
still renders the Rich table with one row showing `n=0  auroc=n/a`. A
"no trajectories matched the filter — exiting" message would be more
useful and would have shortened the four-iteration debug loop in
Phase 3.

### What I checked and found nothing:

- TODO/FIXME/XXX scan: only one TODO, the deliberate Q4 marker in
  `metr_prompt.py:84`.
- Skip/xfail markers: none.
- `except Exception` sites: four, all explicitly justified by
  `noqa: BLE001` and fall through to documented behavior (abstain /
  retry / fallback / None).
- Commented-out code: none.
- Stray `print(`: none (all hits are `console.print` via Rich).
- Mutable default arguments: none.

## 6. Documentation coherence

Read every file in `docs/` and the README. Status per file:

| File | Status | Note |
|---|---|---|
| `README.md` | **accurate** | Reflects v0.1 stress-test framing. References spec.md and followups.md. |
| `docs/spec.md` | **accurate** | Authoritative for v0.1. |
| `docs/writing_a_monitor.md` | **accurate** | Reflects the actual Monitor protocol. |
| `docs/reading_notes.md` | **accurate** (just corrected) | 2,690 → 1,826 fixed. |
| `docs/malt_recon.md` | **accurate** (just corrected + schema note added) | |
| `docs/pivot_decision.md` | **accurate** | Recommendation stands; no figure dependency on the corrected count. |
| `docs/v01_first_run.md` | **accurate** | Phase 3 status doc. |
| `docs/auto_session_questions.md` | **accurate** | Q1-Q5 still open from the user's perspective. |
| `docs/followups.md` | **accurate** | Has dedicated v0.1 section. |
| `docs/refactor_summary.md` | **accurate** | Snapshot of the pre-pivot refactor. |
| `docs/repo_audit.md` | **stale-by-date** | Self-labelled "Produced: 2026-05-25, Git HEAD: 39795a5" — pre-pivot snapshot. Not actively misleading because it's clearly dated. |
| `docs/architecture.md` | **STALE — actively misleading** | Describes the pre-pivot three-layer multi-detector framework as if it's the current design. Heavy use of "Layer 1/2/3", `AuditVerdict`, `integrity_label`. None of these are in v0.1. |
| `docs/exploit-taxonomy.md` | **STALE** | Describes the Layer 2 syntactic scanner's exploit catalog. Layer 2 is not in v0.1. |
| `docs/related-work.md` | **STALE — frames TrajAudit as the pre-pivot thing** | Positions the project against EvilGenie/RHA/TRACE as a "composed multi-layer framework with structured AuditVerdict." Not what v0.1 ships. |
| `examples/README.md` | **STALE** | References `swe_bench_audit.py`, `terminal_bench_audit.py`, `compare_submissions.py` — none of which exist. |

**Contradictions across docs:**

- `architecture.md` calls the project a "post-hoc, benchmark-agnostic
  audit framework" with three layers; `README.md` calls it a
  "stress-test runner for AI safety monitors" with one monitor and three
  transformations. A new reader who finds `architecture.md` first will
  be confused.
- `examples/README.md` promises a `swe_bench_audit.py` example; `spec.md`
  explicitly lists SWE-bench as out of scope for v0.1.
- `related-work.md` claims TrajAudit's "contribution is to compose
  workspace integrity with deterministic AST analysis and an LLM judge";
  v0.1 has none of those.

None of these were created in this PR — they're pre-pivot remnants that
the v0.1 work intentionally didn't touch (per scope discipline). But
they're real coherence issues for any outside reader who browses `docs/`.

## 7. Outside-view check

*Imagined reader: senior researcher at METR or UK AISI clicking a Twitter
link, reading the README, browsing the code for ~5 minutes.*

They'd read the README and decode it correctly: a CLI that stress-tests
monitor degradation under structural transformations of agent
trajectories. The Quickstart shows a working invocation; the illustrative
report card communicates the shape of the output. They'd see the
[![CI](badge)] and a citation block and conclude this is a serious
scaffold. Code structure on a five-minute browse looks clean: typed
Pydantic models, a real Protocol-based monitor surface, 100+ tests,
docstrings throughout. They'd think "OK, this is a reasonable v0.1; the
author cares."

**But they'd hit two friction points on closer look.** First, browsing
`docs/` they'd find `architecture.md` ("a post-hoc, benchmark-agnostic
audit framework that composes deterministic signals…with probabilistic
ones…three independent layers"). That doesn't describe what the README
or `spec.md` say the tool does. Either the README is overselling
simplicity or `architecture.md` is overselling complexity — they wouldn't
immediately know which is current. Second, `examples/README.md` promises
`swe_bench_audit.py`; they'd open `examples/` to find only that README,
no working example. Both of these would erode trust slightly.

**Would they run it?** Probably yes, *if* they're already invested in
monitor evaluation. The Quickstart is realistic and the cost cap is
explicit. The HF auth requirement is fast (5 min) and standard. The
single-monitor scope might read as "this is v0.1, the surface is open" or
as "this only does the one thing METR's blog already did," depending on
mood. If they're not already invested, they'd probably bookmark it,
note the GitHub stars, and decide based on whether v0.2 ships in the
next two months.

**Honest answer to "would they close the tab":** no, not on a five-minute
read. But they would not install it as a primary tool today either —
they'd file it under "interesting, watch for v0.2."

## 8. Recommended next actions

Ranked.

1. **Merge PR #1 with two pre-merge fixes** — *medium effort,
   blocks v0.1 release tag.* Apply M1 (length-mismatch hazard in
   report.py; ~10 lines + 1 test) and delete or stub the four stale
   docs (architecture.md, exploit-taxonomy.md, related-work.md,
   examples/README.md) so an outside reader isn't actively misled.
   Either delete them or replace each with a one-paragraph "this
   describes the pre-pivot framework; see spec.md and pivot_decision.md
   for what TrajAudit actually is." ~30-45 min total. **Without this,
   the outside-view risk in §7 is real.**

2. **Resolve Q5 (live integration) post-merge, locally** — *low effort
   if HF + API key are in hand, ~20 min.* Run `trajaudit run --limit 20
   --budget-usd 3.00` from a normal shell outside Claude Code with a
   real `ANTHROPIC_API_KEY`. Capture the report card and commit
   `docs/v01_first_run.md` updates with real numbers. Unblocks the
   "v0.1 has working numbers" claim. Doesn't block merge of PR #1.

3. **Document the synthesized-transcript-format caveat (L1)** —
   *trivial, ~5 min.* Add a paragraph to `docs/spec.md` under
   "Deviations" noting that `METRPromptMonitor`'s prompt fills METR's
   transcript-chunks placeholder with a synthesized
   `[role:source] content` format, not the agent's literal
   chat-completion messages. Means our AUROC won't match METR's 0.96
   even before sample noise. Without this note, the next person to
   notice the gap will think it's a bug.

4. **Add the defensive tests called out in §5** — *low effort, ~30 min.*
   At minimum: a test for `ScoreRecord(abstain=False,
   monitor_score=None)` in `compute_report` (to lock down the M1 fix);
   a test for orphan-observation handling in `paired_calls` (to lock
   down L4 as intentional behavior). Doesn't block merge.

5. **Version bump `0.0.1` → `0.1.0` and tag a release** — *blocked
   on user.* Touches the `[project]` metadata block, which the
   autonomous-session safeguards exclude. Once Q5 has live numbers
   and the stale docs are cleaned up, this is the natural
   release-ceremony commit. User-only because of Rule 4.

---

Status of `tests/test_report.py`: noted that the file was recently
linted/touched per system reminder. Contents are intact and all 15
tests in it still pass. The post-lint shape matches what was committed
in `5bba744`.
