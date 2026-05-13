"""Top-level orchestrator that runs the three-layer audit pipeline.

The :class:`AuditRunner` accepts a :class:`~trajaudit.core.trajectory.Trajectory`
and dispatches it through (any subset of) the workspace, syntactic, and
semantic layers, then composes their outputs into an
:class:`~trajaudit.core.verdict.AuditVerdict` via
:meth:`AuditVerdict.compose`.

Layer toggles let operators trade off cost vs. coverage:

* Layer 1 needs a Docker daemon and is the most expensive.
* Layer 2 is pure-Python AST work — always cheap.
* Layer 3 depends on an LLM provider; the multi-tier escalation policy
  inside the layer itself decides which providers fire per trajectory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trajaudit.core.trajectory import Trajectory
from trajaudit.core.verdict import AuditVerdict


@dataclass
class AuditConfig:
    """Knobs controlling a single audit run."""

    enable_layer1: bool = True
    enable_layer2: bool = True
    enable_layer3: bool = True
    layer3_providers: list[str] = field(default_factory=lambda: ["vllm", "anthropic"])
    stop_on_first_exploit: bool = False


class AuditRunner:
    """Run the three-layer audit pipeline over one or more trajectories."""

    def __init__(self, config: AuditConfig | None = None) -> None:
        self.config = config or AuditConfig()

    def audit(self, trajectory: Trajectory) -> AuditVerdict:
        """Audit a single trajectory and return its composed verdict."""
        raise NotImplementedError("Phase 1: implement single-trajectory orchestration.")

    def audit_many(self, trajectories: list[Trajectory]) -> list[AuditVerdict]:
        """Audit a batch of trajectories. May parallelize in later phases."""
        raise NotImplementedError("Phase 1: implement batched orchestration.")
