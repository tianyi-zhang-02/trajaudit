"""Local vLLM-served judge provider.

Connects to a locally-running vLLM OpenAI-compatible server. The
cheapest tier of the Layer 3 escalation chain.

The default model is Qwen 2.5 7B Instruct; concrete choice will be
re-evaluated in Phase 4 once we benchmark candidates against
hand-labeled trajectories.

Reads ``VLLM_BASE_URL`` and ``VLLM_MODEL`` from the environment; see
``.env.example``.
"""

from __future__ import annotations

from trajaudit.core.verdict import SemanticVerdict
from trajaudit.layer3_semantic.providers.base import LLMProvider


class VLLMProvider(LLMProvider):
    """vLLM OpenAI-compatible server-backed judge."""

    name = "vllm"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        # Concrete implementation will fall back to os.environ when
        # arguments are None — never hardcode endpoints or keys here.
        self.base_url = base_url
        self.model = model

    def query(self, messages: list[dict[str, str]]) -> SemanticVerdict:
        raise NotImplementedError("Phase 4: implement vLLM client + response parsing.")
