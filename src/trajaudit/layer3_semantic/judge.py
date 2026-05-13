"""LLM judge interface for Layer 3.

The :class:`SemanticJudge` is the single entry point Layer 3 exposes
to the runner. Internally it:

1. Builds prompt messages via :mod:`trajaudit.layer3_semantic.prompts`,
   incorporating Layer 1 and Layer 2 findings as context.
2. Queries the tier-1 provider for a
   :class:`~trajaudit.core.verdict.SemanticVerdict`.
3. Consults
   :class:`~trajaudit.layer3_semantic.escalation.EscalationPolicy` to
   decide, based on the confidence band and the verdict label, whether
   to climb to the next tier.
4. Stamps the final verdict with escalation provenance
   (``escalated`` / ``escalated_from``) so callers can see which tier
   actually produced the answer.

:class:`SemanticJudge` returns a single
:class:`~trajaudit.core.verdict.SemanticVerdict` per trajectory —
never a scalar score.
"""

from __future__ import annotations

from trajaudit.core.trajectory import Trajectory
from trajaudit.core.verdict import SemanticVerdict, SyntacticFinding, WorkspaceFinding


class SemanticJudge:
    """Multi-tier LLM judge.

    The default policy is to query progressively more expensive
    providers until the escalation policy says to stop, or all
    configured providers have been exhausted.
    """

    def __init__(self, providers: list[str] | None = None) -> None:
        self.providers = providers or ["vllm", "anthropic"]

    def judge(
        self,
        trajectory: Trajectory,
        *,
        layer1_findings: list[WorkspaceFinding] | None = None,
        layer2_findings: list[SyntacticFinding] | None = None,
    ) -> SemanticVerdict:
        """Return the Layer 3 :class:`SemanticVerdict` for a trajectory.

        Layer 1 and Layer 2 findings are passed in as context: the
        judge prompt incorporates them so the LLM can reason about
        whether the deterministic detectors' signal is consistent with
        the trajectory's narrative.
        """
        raise NotImplementedError("Phase 4: implement multi-tier judging.")
