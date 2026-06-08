"""Top-level orchestrator that runs the three-layer audit pipeline.

.. note::
   **Phase 0 scaffold. Public API shape is provisional. All runtime
   methods raise** ``NotImplementedError``. Will be substantively
   implemented in Phase 1 once the monitor adapter contract is
   finalized.

The :class:`AuditRunner` accepts a :class:`~monitorstress.core.trajectory.Trajectory`
and dispatches it through (any subset of) the workspace, syntactic, and
semantic layers, then composes their outputs into an
:class:`~monitorstress.core.verdict.AuditVerdict` via
:meth:`AuditVerdict.compose`.

Layer toggles let operators trade off cost vs. coverage:

* Layer 1 needs a Docker daemon and is the most expensive.
* Layer 2 is pure-Python AST work — always cheap.
* Layer 3 depends on an LLM provider; the multi-tier escalation policy
  inside the layer itself decides which providers fire per trajectory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from monitorstress.core.trajectory import Trajectory
from monitorstress.core.verdict import AuditVerdict


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
        """Run all enabled layers over a single trajectory and return the composed verdict.

        Phase 0 scaffold — not yet implemented. Phase 1 will dispatch
        the trajectory through Layers 1, 2, and 3 according to
        :attr:`config`, then call :meth:`AuditVerdict.compose` to
        produce the final structured verdict.
        """
        raise NotImplementedError("Phase 1: implement single-trajectory orchestration.")

    def audit_many(self, trajectories: list[Trajectory]) -> list[AuditVerdict]:
        """Run :meth:`audit` over a batch of trajectories.

        Phase 0 scaffold — not yet implemented. Phase 1 will run
        trajectories sequentially; later phases may parallelize at the
        process or container level depending on which layers are
        enabled.
        """
        raise NotImplementedError("Phase 1: implement batched orchestration.")
