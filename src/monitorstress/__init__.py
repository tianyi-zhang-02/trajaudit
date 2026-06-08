"""TrajAudit — multi-layer audit framework for agent benchmark integrity.

TrajAudit is a post-hoc auditor that ingests agent trajectories from
benchmarks such as SWE-bench Verified and Terminal-Bench, then runs a
three-layer audit pipeline over them:

* :mod:`monitorstress.layer1_workspace` — workspace integrity (Docker
  sandbox replay, filesystem diff, subprocess tracing).
* :mod:`monitorstress.layer2_syntactic` — syntactic exploit detection
  (AST-based pattern matching against a curated exploit taxonomy).
* :mod:`monitorstress.layer3_semantic` — semantic trajectory analysis
  (LLM-as-judge with multi-tier escalation from local vLLM models to
  frontier APIs).

The three layers compose into a
:class:`monitorstress.core.verdict.AuditVerdict` per trajectory — a
structured object with per-layer provenance, a Layer 3 confidence band,
and an explicit ``uncertain`` outcome rather than a single scalar score.
:mod:`monitorstress.reporting` aggregates verdicts into integrity-adjusted
leaderboards and the ``compare`` ranking diff.

See ``docs/architecture.md`` for the conceptual write-up.
"""

from __future__ import annotations

__version__ = "0.0.1"

__all__ = ["__version__"]
