# TrajAudit

**Multi-layer audit framework for agent benchmark integrity.**

[![CI](https://img.shields.io/github/actions/workflow/status/tianyi-zhang-02/trajaudit/ci.yml?branch=main&label=ci)](https://github.com/tianyi-zhang-02/trajaudit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

> Existing work produces benchmarks with hardcoded detectors, taxonomies, or
> single-detector studies. TrajAudit is a **post-hoc, benchmark-agnostic**
> audit framework that composes deterministic signals (AST, workspace diffs)
> with probabilistic ones (LLM-as-judge), and surfaces a **calibrated verdict
> with per-layer provenance** — not a single scalar score.

Three claims, each independently defensible:

- **Framework, not benchmark.** Runs over any benchmark's submitted traces;
  detectors are composable across benchmarks.
- **Provenance over scalar.** A verdict records which layer fired, what fired,
  and where the LLM judge was uncertain, with a confidence band and a
  first-class abstention option.
- **Post-hoc auditor.** No benchmark redesign or harness integration required.
  Audits existing submissions and produces an integrity-adjusted ranking.

## Why this exists

Recent work — METR, EvilGenie (Gabor et al., Nov 2025), RewardHackingAgents
(Atinafu & Cohen, Mar 2026), TRACE (PatronusAI, Jan 2026) — shows that major
agent benchmarks (SWE-bench, Terminal-Bench, WebArena, GAIA, OSWorld) can be
gamed to near-perfect scores without genuinely solving the underlying tasks.
Observed exploits include:

- Pytest collection hooks that auto-pass every test.
- Editing the test file rather than fixing the source bug.
- Writing the harness's expected result file directly, without running the
  suite.
- Monkey-patching the system under test from `conftest.py`.
- Manipulating environment variables that tests read as skip flags.

METR reported `o3` and Claude reward-hacking in 30%+ of eval runs. Standard
pass-rate leaderboards cannot tell these submissions apart from real
solutions. TrajAudit's job is to make the difference visible.

## How it works

TrajAudit runs three independent layers over each trajectory and composes
their outputs into a single structured `AuditVerdict`.

- **Layer 1 — Workspace integrity.** Replays the trajectory in a Docker
  sandbox, snapshots the filesystem before and after, classifies the diff,
  and traces the subprocess commands the agent issued. Catches the *physical*
  signal of cheating: tests modified, result files fabricated, harness
  bypassed.
- **Layer 2 — Syntactic exploit detection.** Walks the AST of every code edit
  the agent made and matches against a curated catalog of known exploit
  patterns. Fast, deterministic, runs first. Catches *known* shapes of
  cheating, regardless of how they were dressed up.
- **Layer 3 — Semantic trajectory analysis.** Hands the trajectory plus the
  Layer 1+2 findings to an LLM judge and asks for a structured verdict:
  `{exploit_likely, clean, abstain}` with a closed confidence band and
  taxonomy tags. Multi-tier escalation runs a small local model first
  (Qwen 2.5 7B via vLLM) and only climbs to a frontier API when the local
  judge is uncertain. Catches *novel* exploits the rules don't cover.

The final per-trajectory artifact is an `AuditVerdict` with all three layers'
findings attached and an `integrity_label ∈ {clean, suspect, exploit, uncertain}`.
`uncertain` is a first-class outcome — TrajAudit would rather say "I don't
know" than coerce a binary call.

## Status

**Phase 0 — scaffold. Not yet functional.** All public-API shapes are in
place (`Trajectory`, `Step`, `SemanticVerdict`, `AuditVerdict`); every
runtime function raises `NotImplementedError`. See the roadmap for what
lands when.

## Roadmap

- [x] **Phase 0 — Scaffold.** Package skeleton, CI, docs, stub modules,
  verdict schemas as public API.
- [ ] **Phase 1 — Trajectory model + SWE-bench adapter.** Survey
  OpenInference / Inspect AI / AgentOps; subclass if close enough rather
  than invent a fourth standard. 3–5 public SWE-agent / OpenHands traces as
  fixtures.
- [ ] **Phase 2 — Layer 2 syntactic scanner.** AST detection of the five
  exploit patterns in the taxonomy. Evaluated against EvilGenie + RHA
  labeled hacks, not synthetic. Target ≥ 90% recall, ≤ 5% FP.
- [ ] **Phase 3 — Layer 1 workspace sandbox.** Docker replay reusing
  SWE-bench eval images; FS diff; subprocess tracing. Loudly flag verdicts
  where environment reconstruction is imperfect.
- [ ] **Phase 4 — Layer 3 LLM judge.** Tier-1 local vLLM (Qwen 2.5 7B) →
  Tier-2 frontier API on uncertainty / contradictory L1+L2 signal. ~100
  trajectories for v1 validation.
- [ ] **Phase 5 — Reporting + `compare` CLI.** JSON / Markdown / CSV
  exporters; integrity-adjusted leaderboards; `trajaudit compare` ranking
  diff between submissions.
- [ ] **Phase 6 — Coverage expansion + writeup.** Terminal-Bench, WebArena,
  GAIA, OSWorld adapters. Public findings post.

## Related Work

The reward-hacking-detection space had three clusters as of mid-2026.
TrajAudit sits in the gap between them — framework rather than benchmark,
composed rather than single-detector, structured-verdict rather than scalar.
See [docs/related-work.md](docs/related-work.md) for the long version.

- **EvilGenie** (Gabor et al., Nov 2025) — a LiveCodeBench-derived benchmark
  with labeled reward-hacking cases. *TrajAudit differs:* EvilGenie is a
  benchmark with embedded labels; TrajAudit is a framework that runs over
  any benchmark's submissions. EvilGenie's labels are an evaluation set for
  TrajAudit's Layer 2.
- **RewardHackingAgents (RHA)** (Atinafu & Cohen, Mar 2026) —
  ML-engineering workspace with patch tracking and hardcoded
  workspace-integrity detectors. *TrajAudit differs:* RHA effectively
  occupies the "Layer-1-only" niche. TrajAudit's contribution is to compose
  workspace integrity with deterministic AST analysis and an LLM judge,
  and to expose the disagreement structure between them.
- **TRACE** (PatronusAI, Jan 2026) — synthetic trajectory generation for
  trajectory-judge training data. *TrajAudit differs:* TRACE generates
  data; TrajAudit consumes it. TrajAudit avoids relying solely on
  synthetic data for its evaluation claims — synthetic is the floor,
  real labeled hacks (EvilGenie / RHA) are the bar.
- **TrajAD** (Feb 2026) — a fine-tuned Qwen3-4B trajectory anomaly
  classifier. *TrajAudit differs (and the names are close, so read
  carefully):* TrajAD ships a single neural classifier whose output is a
  black-box score; TrajAudit ships a composed multi-layer framework whose
  output is a structured `AuditVerdict` with per-layer provenance, a
  confidence band, and explicit abstention. TrajAD could plug *into*
  TrajAudit's Layer 3 as one provider; the converse doesn't make sense.
- **COBA** (ICML 2026) — component-based agent behavior auditing.
  *TrajAudit differs:* COBA is a methodological framing applied to a
  specific eval; TrajAudit is the open-source tool that operationalizes
  the framing for a defined target — agent benchmark submissions — with
  a stable verdict schema and a CLI. (The author of this project also
  co-authored the COBA paper from the NVIDIA × GT EIC Lab collaboration.)

## Installation

Not yet on PyPI. Install from source:

```bash
git clone https://github.com/tianyi-zhang-02/trajaudit
cd trajaudit
uv sync --all-extras
```

Once on PyPI (post-Phase 2):

```bash
pip install trajaudit
```

## Citation

If you use TrajAudit in research, please cite it as:

```bibtex
@software{trajaudit,
  author  = {Zhang, Tianyi},
  title   = {{TrajAudit}: Multi-layer audit framework for agent benchmark integrity},
  year    = {2026},
  url     = {https://github.com/tianyi-zhang-02/trajaudit},
  version = {0.0.1}
}
```

## License

MIT — see [LICENSE](LICENSE).
