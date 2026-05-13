"""Core data models and orchestration for TrajAudit.

This package defines the benchmark-agnostic primitives that flow through
the three audit layers:

* :mod:`trajaudit.core.trajectory` — the input: a record of what an
  agent did on a single benchmark task.
* :mod:`trajaudit.core.verdict` — the output: a structured
  :class:`~trajaudit.core.verdict.AuditVerdict` with per-layer findings,
  a Layer 3 confidence band, and an explicit ``uncertain`` outcome.
* :mod:`trajaudit.core.runner` — the orchestrator that wires the three
  layers together and produces verdicts.
"""

from __future__ import annotations
