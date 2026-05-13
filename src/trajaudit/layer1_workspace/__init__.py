"""Layer 1 — Workspace Integrity.

This layer replays the agent's trajectory inside an isolated Docker
sandbox and observes the workspace deltas that result. Its job is to
catch exploits whose signal is *physical* — files in the wrong place,
the test runner never invoked, network calls in an offline benchmark.

Layer 1's `WorkspaceFinding` outputs participate in the composed
:class:`~trajaudit.core.verdict.AuditVerdict` and feed the Layer 3
judge as context.

Submodules:

* :mod:`trajaudit.layer1_workspace.sandbox` — Docker sandbox.
* :mod:`trajaudit.layer1_workspace.fs_differ` — filesystem diff.
* :mod:`trajaudit.layer1_workspace.process_tracer` — subprocess tracing.
"""

from __future__ import annotations
