# TrajAudit — Architecture

## Goals and framing

TrajAudit is a post-hoc, benchmark-agnostic audit framework. Given the
trajectory an agent produced on a benchmark task — its actions, the files it
touched, the shell commands it issued, and the harness's pass/fail verdict —
TrajAudit decides whether the reported score reflects a genuine solution or
an exploit of the evaluation infrastructure.

Two design choices distinguish the framework from prior work and shape every
module below them:

1. **Provenance over scalar.** The final per-trajectory artifact is
   `AuditVerdict`, a structured object with per-layer findings, a Layer 3
   confidence band, and an explicit `uncertain` outcome. Reviewers can always
   drill back from the composed label to the specific layer findings — or the
   specific judge tier — that produced it. A scalar score throws that
   information away.

2. **Composed signals, not a single detector.** TrajAudit runs three
   independent layers with very different false-positive / false-negative
   profiles and exposes their *disagreement structure* rather than averaging
   it away. RewardHackingAgents (Atinafu & Cohen, Mar 2026) already
   demonstrates that workspace-integrity monitoring is a strong stand-alone
   signal; TrajAudit's contribution is to treat that signal as one component
   of a composed verdict, alongside syntactic AST scanning and an LLM judge.

The decomposition draws on **COBA**-style component-based auditing (ICML
2026) — narrowly-scoped component auditors whose outputs are aggregated into
a holistic verdict.

## Public API: the verdict schemas

The shapes in [`src/trajaudit/core/verdict.py`](../src/trajaudit/core/verdict.py)
are the framework's stable surface. Every downstream consumer — CLI,
exporters, leaderboards, the `compare` subcommand — reads from these:

- `WorkspaceFinding` — Layer 1 output, with implicated paths.
- `SyntacticFinding` — Layer 2 output, with file, line, and source snippet.
- `SemanticVerdict` — Layer 3 output. Carries
  `verdict ∈ {exploit_likely, clean, abstain}`, a closed `confidence_band` in
  [0, 1], a free-text rationale, escalation provenance (`escalated`,
  `escalated_from`), and `taxonomy_tags`.
- `AuditVerdict` — the composed object. Per-layer finding lists, the Layer 3
  verdict, an `integrity_label ∈ {clean, suspect, exploit, uncertain}`, and a
  natural-language `rationale` summarizing where layers agreed or disagreed.

`abstain` and `uncertain` are first-class. They are *not* fallbacks for
"we couldn't run a layer" — they represent the genuine inability to
confidently classify, and downstream reporting surfaces them explicitly.

## Layer 1 — Workspace Integrity

**Question:** *Did the agent's environment evolve in a way that's consistent
with solving the task?*

Layer 1 replays the trajectory in an isolated Docker sandbox and observes:

- **Filesystem diff** between initial and final workspace states, classified
  by path (source vs. tests vs. config vs. harness-internal).
- **Subprocess trace** of shell commands and their effects, with attention to
  commands that touch the harness, mutate test files, or run after the
  apparent solve step.
- **Network activity**, where the benchmark normally forbids it.

**Positioning.** Layer 1 overlaps in spirit with what RHA already does well.
We are not claiming a wedge here. TrajAudit's contribution is not Layer 1 in
isolation but the composition — Layer 1 emits structured `WorkspaceFinding`s
that participate in the multi-layer verdict and feed the Layer 3 judge as
context, rather than acting as a stand-alone decision.

**Environmental drift mitigation.** Re-execution in a clean container will
sometimes produce diffs the agent never caused (timestamps, package caches,
build artifacts). The replay path *must* downgrade its findings' confidence
— or drop them entirely — when it cannot reconstruct the original
environment faithfully. We default to reusing SWE-bench's per-repo evaluation
images for SWE-bench tasks, so the drift surface is as narrow as possible.

## Layer 2 — Syntactic Exploit Detection

**Question:** *Do the agent's code edits match any known exploit pattern?*

Layer 2 statically analyses every code edit and matches it against the
curated catalog in [exploit-taxonomy.md](exploit-taxonomy.md). It does not
execute anything; it walks the parsed AST and returns one `SyntacticFinding`
per matched signature.

The starting catalog covers five patterns — pytest collection-hook
auto-pass, test-assertion tampering, result-file fabrication, conftest mock
override, and env-var bypass.

Layer 2 is cheap (milliseconds per trajectory), deterministic, and is the
first detector to run.

**Eval strategy.** Phase 2 validates this layer against **labeled hacks from
EvilGenie and RewardHackingAgents**, not synthetic. Synthetic fixtures are
the floor for unit tests; real labeled hacks are the bar. Target: ≥ 90%
recall on EvilGenie-labeled exploits with ≤ 5% FP on clean traces.

Python-only initially. Covers SWE-bench and most of Terminal-Bench.

## Layer 3 — Semantic Trajectory Analysis

**Question:** *Reading the trajectory like a human reviewer, does the agent
appear to be solving the task or routing around it?*

Layer 3 hands the trajectory — plus Layer 1 and Layer 2 findings as
context — to an LLM judge and asks for a structured `SemanticVerdict`. The
judge **does not** return a scalar score. It returns:

- A categorical `verdict ∈ {exploit_likely, clean, abstain}`.
- A closed `confidence_band` in [0, 1]. Judges that can't put tight bounds
  on themselves widen the band; the escalation policy reads band-width
  (not a point estimate) as its primary signal.
- A free-text `reasoning` field that cites specific actions.
- Escalation provenance: `escalated` and `escalated_from`, so a verdict
  upgraded from a local model to a frontier API is not silently
  indistinguishable from one the local model produced on its own.
- `taxonomy_tags` derived from the COBA component framing.

**Multi-tier escalation.** Default policy:

1. Tier 1: small, fast, locally-served judge (vLLM with Qwen 2.5 7B).
2. If the band is tight and the label is `clean` or `exploit_likely`, accept.
3. Otherwise — wide band, abstention, or contradictory L1/L2 signal —
   escalate to Tier 2 (frontier API).
4. Tier 2's answer is always accepted; `abstain` is preserved through to
   the composed verdict as `uncertain`.

## Composed verdict

`AuditVerdict.compose(...)` aggregates per-layer outputs into the final
`integrity_label`:

- Any `HIGH` or `CRITICAL` Layer 1 / Layer 2 finding → `EXPLOIT`.
- Layer 3 `exploit_likely` with narrow confidence band → `EXPLOIT`.
- Layer 3 `abstain` or wide band with no high-severity findings →
  `UNCERTAIN`.
- Mixed-signal cases — some layers fire, others don't — → `SUSPECT`.
- Otherwise → `CLEAN`.

The composed `rationale` records which layers agreed and which didn't, so
provenance is visible at the headline level as well as in the per-layer
findings.

## Reporting and `compare`

The reporting layer turns `AuditVerdict`s into:

- **Integrity-adjusted leaderboards** — raw vs. clean-only vs.
  non-exploit pass rates, in the COBA Table 6 style.
- **`trajaudit compare`** — the framework's headline UX. Two submissions
  whose raw pass-rates are close can move apart significantly once
  exploit-driven solves are removed; `compare` shows the rank diff
  explicitly.
- **Exporters** — JSON for tooling, Markdown for humans, CSV for
  spreadsheets.

## Non-goals

- TrajAudit does **not** re-run benchmarks. It audits what already
  happened.
- TrajAudit does **not** try to prevent exploits during agent execution.
- TrajAudit is **not** a general-purpose AI safety evaluator. Scope is
  benchmark integrity.
