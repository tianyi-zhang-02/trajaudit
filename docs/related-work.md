# TrajAudit — Related Work

Owning the comparisons up front is part of the framework's positioning.
This doc is intentionally adversarial: for each cluster of prior work,
what it does well, what TrajAudit takes from it, and where TrajAudit
differs.

The space had three clusters as of mid-2026.

---

## Cluster 1 — Benchmarks that demonstrate reward hacking

Benchmarks (with hardcoded detectors or labels) rather than auditing
frameworks.

### EvilGenie — Gabor et al., November 2025

A LiveCodeBench-derived benchmark with labeled reward-hacking cases.

- **What it does well.** Provides a labeled evaluation set on real
  code-task trajectories, which is rare. Labels are usable for held-out
  evaluation of new detectors.
- **What TrajAudit takes.** EvilGenie's labeled hacks are the primary
  evaluation set for TrajAudit's Layer 2 in Phase 2 (target ≥ 90% recall,
  ≤ 5% FP). Using a real labeled set, instead of synthetic fixtures,
  breaks the circularity of "we wrote the detector and the test cases
  that pass it".
- **Where TrajAudit differs.** EvilGenie is a benchmark with a taxonomy
  embedded in it. TrajAudit is a framework with a composable detector
  pipeline that can be evaluated *against* EvilGenie and run *over* any
  benchmark.

### RewardHackingAgents (RHA) — Atinafu & Cohen, March 2026

ML-engineering workspace tasks with explicit patch tracking and hardcoded
detectors for workspace-integrity violations.

- **What it does well.** Workspace-integrity monitoring done right: patch
  tracking is built into the task surface, not bolted on. RHA effectively
  occupies the niche a "Layer-1-only" tool would.
- **What TrajAudit takes.** Validation that workspace integrity is a real,
  high-precision signal. Implementation cues for FS diff and patch
  tracking.
- **Where TrajAudit differs.** Critically, Layer 1 is **not** TrajAudit's
  wedge — RHA already covers it. TrajAudit's contribution is the
  composition of Layer 1 with deterministic AST analysis (Layer 2) and an
  LLM judge with structured uncertainty (Layer 3), plus a
  benchmark-agnostic verdict schema with per-layer provenance.

### Reward Hacking Benchmark — Thaman et al., May 2026

Multi-step tool-use scenarios designed to elicit reward hacking.

- **What TrajAudit takes.** Useful as a source of additional positive
  examples for Layer 3 evaluation, especially for multi-step trajectories
  where Layer 2's per-edit AST signal is weaker.
- **Where TrajAudit differs.** Benchmark vs. framework, again.

### TRACE — PatronusAI, January 2026

Synthetic trajectory generation for judge training.

- **What TrajAudit takes.** Approach for generating synthetic positive
  trajectories when expanding Layer 3 training/eval data — useful as a
  *floor* for coverage rather than as a primary eval set.
- **Where TrajAudit differs.** TrajAudit does not rely solely on synthetic
  data for its eval claims. Synthetic is the floor; real labeled hacks
  (EvilGenie / RHA) are the bar.

---

## Cluster 2 — Trajectory-level anomaly classifiers

A single classifier model that ingests trajectories and emits a label or
score.

### TrajAD — February 2026

A fine-tuned Qwen3-4B trajectory anomaly detector.

**The names are close — TrajAD vs. TrajAudit — so this distinction matters.**

- **What TrajAD is.** A single neural classifier. Input: trajectory.
  Output: a scalar or binary label. End-to-end black-box.
- **What TrajAudit is.** A composed framework. Input: trajectory.
  Output: a structured `AuditVerdict` with per-layer findings, a
  confidence band, escalation provenance, and an explicit abstention
  option.
- **The relationship.** TrajAD could plug *into* TrajAudit as one Layer 3
  provider — a fine-tuned local judge. The converse doesn't make sense:
  you can't wrap TrajAudit's composed verdict structure inside a
  single-scalar classifier.
- **Where TrajAudit differs.** TrajAD ships a *classifier*; TrajAudit
  ships a *system* that composes a classifier (Layer 3) with
  deterministic signals (Layers 1 + 2) and exposes the disagreement
  structure between them. The disagreement structure is the artifact
  TrajAudit cares about — a single black-box neural classifier hides
  exactly that structure.

### ATBench, PolicyGuardBench, COBA

Component-based agent behavior auditing. **COBA** (ICML 2026) is
particularly relevant — its decomposition of "auditing" into
narrowly-scoped component auditors directly inspires TrajAudit's
three-layer split and the `taxonomy_tags` field on `SemanticVerdict`.
(The author of this project also co-authored the COBA paper from the
NVIDIA × GT EIC Lab collaboration.)

- **Where TrajAudit differs.** COBA is a methodological framing applied
  to a specific eval. TrajAudit is the open-source tool that
  operationalizes the framing for a defined target — agent benchmark
  submissions — with a stable verdict schema and a CLI.

---

## Cluster 3 — Judge-based detection

Single-judge, scalar or binary output. METR, Palisade, and Anthropic's
internal evals predominantly fall here.

- **What this cluster does well.** Catches contextual, novel exploits
  that no rule catalog can express.
- **What TrajAudit takes.** The basic premise — that an LLM judge with
  the full trajectory in context is a powerful detector — is the
  foundation of TrajAudit's Layer 3.
- **Where TrajAudit differs.** Scalar judge outputs project a
  false-precision number ("0.73") onto a fundamentally ambiguous
  decision. TrajAudit's `SemanticVerdict` returns a categorical label
  with a **confidence band**, an explicit **`abstain`** option, and
  **escalation provenance** so a frontier-tier upgrade is visible to
  the caller.

---

## Synthesis

| | Cluster 1 (benchmarks) | Cluster 2 (classifiers) | Cluster 3 (single-judge) | TrajAudit |
|---|:-:|:-:|:-:|:-:|
| Benchmark-agnostic | ✗ | ✓ | ✓ | ✓ |
| Composable signals | ✗ | ✗ | ✗ | ✓ |
| Structured verdict + provenance | ✗ | ✗ | ✗ | ✓ |
| Calibrated uncertainty + abstention | ✗ | ✗ | partial | ✓ |
| Post-hoc, no harness changes | partial | ✓ | ✓ | ✓ |

The framework's three design choices — composition, provenance, calibrated
uncertainty — each cite a specific gap in the prior literature above.
