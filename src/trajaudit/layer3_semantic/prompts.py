"""Prompt templates for the Layer 3 LLM judge.

Prompts are kept in one module to make them easy to audit and version.
Each builder takes a structured input (a trajectory plus the upstream
layers' findings) and returns the system + user messages a provider
should send.

The judge prompt is **taxonomy-guided**: it incorporates the COBA
component framing and asks the judge to attach
:attr:`~trajaudit.core.verdict.SemanticVerdict.taxonomy_tags` to its
output. Including Layer 1 and Layer 2 findings as context lets the
judge reason about agreement between deterministic and probabilistic
signals — disagreement is itself useful evidence and drives
escalation.

Versioning note: when changing a prompt in a way that could move
verdicts, bump :data:`PROMPT_VERSION` — downstream reports include the
version so retroactive comparison is possible.
"""

from __future__ import annotations

from trajaudit.core.trajectory import Trajectory
from trajaudit.core.verdict import SyntacticFinding, WorkspaceFinding

PROMPT_VERSION: str = "v0"

#: Phase 4 fills in the body. Kept as a module-level constant so the
#: judge implementation and any future templating tooling have a single
#: well-known address to reference.
JUDGE_PROMPT_TEMPLATE: str = ""


def build_judge_messages(
    trajectory: Trajectory,
    *,
    layer1_findings: list[WorkspaceFinding] | None = None,
    layer2_findings: list[SyntacticFinding] | None = None,
) -> list[dict[str, str]]:
    """Build the chat-style messages for a single judge call."""
    raise NotImplementedError("Phase 4: implement judge prompt template.")


def build_taxonomy_briefing() -> str:
    """Return the static portion of the prompt describing the exploit taxonomy."""
    raise NotImplementedError("Phase 4: implement taxonomy briefing.")
