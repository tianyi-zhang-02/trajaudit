"""Layer 2 — Syntactic Exploit Detection.

Layer 2 statically analyses every code edit the agent made and matches
it against a curated catalog of known exploit patterns. It is cheap,
deterministic, and runs without any sandbox or LLM call — the first
detector in the pipeline.

Submodules:

* :mod:`trajaudit.layer2_syntactic.code_extractor` — pull every
  ``before`` / ``after`` source pair out of a trajectory.
* :mod:`trajaudit.layer2_syntactic.exploit_signatures` — the curated
  catalog of exploit signatures (one per entry in the taxonomy).
* :mod:`trajaudit.layer2_syntactic.ast_scanner` — the scanner that
  walks the AST of each edit and matches signatures.
"""

from __future__ import annotations
