"""Multi-tier escalation policy for the Layer 3 judge.

Querying a frontier API for every trajectory is wasteful — most
trajectories are obviously clean, and a small local model can dispatch
them confidently. The :class:`EscalationPolicy` decides, given the
current tier's :class:`~trajaudit.core.verdict.SemanticVerdict`,
whether to accept it or climb to the next tier.

The decision is driven by the **confidence band width**, not by a
point estimate: a judge that is honest about its uncertainty widens
the band, and the policy reads that directly.

Default policy:

1. Start at the cheapest configured provider (typically local vLLM).
2. If band-width ≤ ``stop_band_width`` and the verdict is ``clean`` or
   ``exploit_likely``, accept.
3. If the verdict is ``abstain`` at the cheapest tier, escalate
   (perhaps a stronger model can decide).
4. If contradictory L1/L2 signal was provided as context and the
   verdict is ``clean``, escalate once.
5. Final tier's answer is always accepted; ``abstain`` is preserved
   through to the composed verdict as ``UNCERTAIN``.
"""

from __future__ import annotations

from dataclasses import dataclass

from trajaudit.core.verdict import (
    SemanticLabel,
    SemanticVerdict,
    SyntacticFinding,
    WorkspaceFinding,
)


@dataclass
class EscalationPolicy:
    """Configurable escalation thresholds."""

    stop_band_width: float = 0.20
    max_tiers: int = 3

    def should_escalate(
        self,
        verdict: SemanticVerdict,
        *,
        tier: int,
        layer1_findings: list[WorkspaceFinding] | None = None,
        layer2_findings: list[SyntacticFinding] | None = None,
    ) -> bool:
        """Decide whether to escalate after seeing ``verdict`` at ``tier``.

        ``tier`` is 0-based; ``tier == self.max_tiers - 1`` means we
        are already at the last tier and cannot escalate further.
        """
        raise NotImplementedError("Phase 4: implement escalation decision.")

    @staticmethod
    def annotate_escalation(
        verdict: SemanticVerdict, *, from_tier: str
    ) -> SemanticVerdict:
        """Return ``verdict`` with escalation provenance stamped on it."""
        return verdict.model_copy(
            update={"escalated": True, "escalated_from": from_tier}
        )

    @staticmethod
    def _label_is_decisive(label: SemanticLabel) -> bool:
        return label in (SemanticLabel.CLEAN, SemanticLabel.EXPLOIT_LIKELY)
