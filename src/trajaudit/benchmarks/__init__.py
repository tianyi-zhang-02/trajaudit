"""Benchmark adapters.

Each benchmark TrajAudit supports gets a thin adapter that translates
the benchmark's native trajectory format into the schema defined in
:mod:`trajaudit.core.trajectory`, and supplies the path classifier
that Layer 1 uses to interpret workspace diffs.

Currently planned:

* :mod:`trajaudit.benchmarks.swe_bench` — SWE-bench Verified.
* :mod:`trajaudit.benchmarks.terminal_bench` — Terminal-Bench.

The :class:`~trajaudit.benchmarks.base.BenchmarkAdapter` base class
defines the contract every adapter implements.
"""

from __future__ import annotations
