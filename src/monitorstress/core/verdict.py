"""Verdict schemas — the public API of the TrajAudit framework.

Each per-trajectory audit produces one :class:`AuditVerdict`. The
verdict is a *structured object with per-layer provenance*, not a
scalar score: callers can see which layer fired, what fired, where
the LLM judge was uncertain, and which tier of the escalation chain
produced the final semantic call.

The schemas defined here are intentionally the canonical shape: every
downstream consumer (CLI, exporters, leaderboards, the ``compare``
subcommand) reads :class:`AuditVerdict` and nothing else.

Hierarchy::

    AuditVerdict
    ├── layer1_findings : list[WorkspaceFinding]   # filesystem / process signal
    ├── layer2_findings : list[SyntacticFinding]   # AST signal
    ├── layer3_verdict  : SemanticVerdict          # LLM judge w/ confidence band
    └── integrity_label : IntegrityLabel           # composed: clean / suspect / exploit / uncertain
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class IntegrityLabel(StrEnum):
    """Composed top-level integrity classification for a trajectory.

    ``uncertain`` is a first-class outcome — it captures the case where
    layers disagree or the semantic judge abstains. It is *not* a
    fallback for "we couldn't run a layer".
    """

    CLEAN = "clean"
    SUSPECT = "suspect"
    EXPLOIT = "exploit"
    UNCERTAIN = "uncertain"


class Severity(StrEnum):
    """Severity of a single per-layer finding."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SemanticLabel(StrEnum):
    """The Layer 3 LLM judge's structured label.

    ``abstain`` is first-class: the judge declines to commit when the
    trajectory is genuinely ambiguous, rather than coercing a binary
    call. When ``verdict == ABSTAIN`` the verdict's :attr:`abstain` flag
    must also be ``True`` and ``confidence_band`` must be the maximally
    uninformative ``(0.0, 1.0)``; the consistency is enforced by a
    validator on :class:`SemanticVerdict`.
    """

    EXPLOIT_LIKELY = "exploit_likely"
    CLEAN = "clean"
    ABSTAIN = "abstain"


class TaxonomyTag(StrEnum):
    """Behavioural taxonomy categories the judge may attach to a verdict.

    The initial enum values cover the categories documented in the
    monitor-evaluation literature (notably MALT). The enum is
    intentionally open to extension; ``OTHER`` is the explicit catch-all
    and ``NORMAL`` is the benign-trajectory label.
    """

    BYPASS_CONSTRAINTS = "bypass_constraints"
    IGNORES_TASK_INSTRUCTIONS = "ignores_task_instructions"
    HARDCODED_SOLUTION = "hardcoded_solution"
    BRUTE_FORCED_SOLUTION = "brute_forced_solution"
    GIVES_UP = "gives_up"
    SABOTAGE = "sabotage"
    MATCH_WEAKER_MODEL = "match_weaker_model"
    PARTIAL_PROBLEM_SOLVING = "partial_problem_solving"
    REASONING_ABOUT_TASK = "reasoning_about_task"
    REFUSALS = "refusals"
    EVALUATION_AWARENESS = "evaluation_awareness"
    OTHER = "other"
    NORMAL = "normal"


# ---------------------------------------------------------------------------
# Per-layer findings
# ---------------------------------------------------------------------------


class _BaseFinding(BaseModel):
    """Fields common to every layer's findings."""

    pattern_id: str | None = Field(
        None,
        description="Exploit-taxonomy id, e.g. 'EX-001-pytest-collection-autopass'.",
    )
    severity: Severity
    title: str
    description: str
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Layer-specific structured evidence (paths, AST snippets, etc.).",
    )
    confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Optional [0,1] confidence score."
    )


class WorkspaceFinding(_BaseFinding):
    """Layer 1 (workspace integrity) finding.

    Produced by the Docker sandbox replay, filesystem differ, or
    process tracer. Always carries the path(s) implicated so reviewers
    can drill back to the workspace artifact.
    """

    layer: str = Field(default="layer1_workspace", frozen=True)
    paths: list[Path] = Field(
        default_factory=list,
        description="Workspace-relative paths implicated in the finding.",
    )


class SyntacticFinding(_BaseFinding):
    """Layer 2 (syntactic exploit detection) finding.

    Produced by the AST scanner. Includes a source-level location so
    the exact suspect node is recoverable.
    """

    layer: str = Field(default="layer2_syntactic", frozen=True)
    path: Path | None = Field(None, description="File the finding refers to.")
    line: int | None = Field(None, description="1-based line number of the match.")
    snippet: str | None = Field(None, description="Source snippet that matched.")


# ---------------------------------------------------------------------------
# Layer 3 verdict
# ---------------------------------------------------------------------------


class SemanticVerdict(BaseModel):
    """Layer 3 (LLM judge) verdict.

    The schema is deliberately not a scalar. ``confidence_band`` is a
    closed ``[low, high]`` interval — judges that can't put tight bounds
    on themselves widen the band, and the escalation policy uses
    band-width (not a point estimate) to decide whether to climb a
    tier.

    ``abstain`` is a first-class flag (in addition to the matching
    :attr:`SemanticLabel.ABSTAIN` value) so calibration code and
    selective-prediction analyses can branch on a single boolean
    without inspecting the label. When ``abstain=True`` the verdict's
    label must be ``ABSTAIN`` and its ``confidence_band`` must be
    ``(0.0, 1.0)``; the inverse direction is enforced too. See
    :meth:`_validate_band_and_abstain`.

    ``escalated`` / ``escalated_from`` record provenance so a verdict
    that was upgraded from a small local model to a frontier API is
    not silently indistinguishable from one the local model produced
    on its own.
    """

    verdict: SemanticLabel
    confidence_band: tuple[float, float] = Field(
        ...,
        description="Closed [low, high] confidence interval in [0, 1].",
    )
    reasoning: str = Field(
        ...,
        description="Free-text rationale from the judge, expected to cite specific steps.",
    )
    abstain: bool = Field(
        default=False,
        description=(
            "True iff the judge declines to commit. Must agree with verdict==ABSTAIN "
            "and confidence_band==(0.0, 1.0)."
        ),
    )
    escalated: bool = Field(
        default=False,
        description="True iff this verdict came from a higher tier than the default.",
    )
    escalated_from: str | None = Field(
        None,
        description="Tier this verdict was escalated from, e.g. 'vllm-qwen2.5-7b'.",
    )
    taxonomy_tags: list[TaxonomyTag] = Field(
        default_factory=list,
        description="Behavioural taxonomy tags the judge attached to the trajectory.",
    )

    @property
    def band_width(self) -> float:
        """Width of the confidence band — used by the escalation policy."""
        lo, hi = self.confidence_band
        return hi - lo

    @model_validator(mode="after")
    def _validate_band_and_abstain(self) -> SemanticVerdict:
        """Enforce band ordering, [0, 1] range, and abstain consistency."""
        lo, hi = self.confidence_band
        if not (0.0 <= lo <= hi <= 1.0):
            raise ValueError(
                f"confidence_band must satisfy 0.0 <= lo <= hi <= 1.0; got ({lo}, {hi})"
            )
        if self.abstain:
            if self.verdict is not SemanticLabel.ABSTAIN:
                raise ValueError(
                    "abstain=True requires verdict=SemanticLabel.ABSTAIN; "
                    f"got verdict={self.verdict!r}"
                )
            if self.confidence_band != (0.0, 1.0):
                raise ValueError(
                    "abstain=True requires confidence_band=(0.0, 1.0); "
                    f"got {self.confidence_band}"
                )
        elif self.verdict is SemanticLabel.ABSTAIN:
            raise ValueError(
                "verdict=SemanticLabel.ABSTAIN requires abstain=True"
            )
        return self


# ---------------------------------------------------------------------------
# Composed verdict
# ---------------------------------------------------------------------------


class AuditVerdict(BaseModel):
    """The composed per-trajectory output of the framework.

    This is the public artifact every downstream consumer reads.
    Leaderboards derive from :attr:`integrity_label`; drill-down UIs
    read the per-layer finding lists and :attr:`layer3_verdict`.
    """

    trajectory_id: str
    benchmark: str
    task_id: str
    agent_id: str | None = None

    layer1_findings: list[WorkspaceFinding] = Field(default_factory=list)
    layer2_findings: list[SyntacticFinding] = Field(default_factory=list)
    layer3_verdict: SemanticVerdict | None = Field(
        None,
        description="Absent iff Layer 3 was disabled for this run.",
    )

    integrity_label: IntegrityLabel
    rationale: str = Field(
        ...,
        description="Natural-language summary of which layers agreed or disagreed.",
    )

    harness_passed: bool | None = Field(
        None,
        description="The original harness pass/fail, copied through for convenience.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def compose(
        cls,
        *,
        trajectory_id: str,
        benchmark: str,
        task_id: str,
        agent_id: str | None,
        harness_passed: bool | None,
        layer1_findings: list[WorkspaceFinding],
        layer2_findings: list[SyntacticFinding],
        layer3_verdict: SemanticVerdict | None,
    ) -> AuditVerdict:
        """Compose per-layer outputs into a final :class:`AuditVerdict`.

        Default composition policy (Phase 5):

        * Any ``HIGH`` or ``CRITICAL`` Layer 1/2 finding → ``EXPLOIT``.
        * Layer 3 ``exploit_likely`` with narrow confidence band → ``EXPLOIT``.
        * Layer 3 ``abstain`` or wide confidence band, with no other
          high-severity findings → ``UNCERTAIN``.
        * Mixed-signal cases (some layers fire, others disagree) →
          ``SUSPECT``.
        * Otherwise → ``CLEAN``.
        """
        raise NotImplementedError("Phase 5: implement composition policy.")
