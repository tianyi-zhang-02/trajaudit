"""Layer 3 — Semantic Trajectory Analysis.

Layer 3 hands the trajectory to an LLM judge — together with Layer 1
and Layer 2 findings as context — and asks whether, read end-to-end,
the agent appears to be solving the task or routing around it. This
catches novel, contextual exploits that the rule-based layers cannot
pattern-match.

Cost is managed via a multi-tier escalation policy: cheap local
models first, frontier APIs only on hard cases. See
:mod:`trajaudit.layer3_semantic.escalation` for the policy and
:mod:`trajaudit.layer3_semantic.providers` for the model backends.
"""

from __future__ import annotations
