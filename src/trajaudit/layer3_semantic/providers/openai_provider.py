"""OpenAI judge provider.

Frontier tier in the Layer 3 escalation chain. Used as an alternative
to (or in addition to) the Anthropic provider, depending on operator
preference.

Reads ``OPENAI_API_KEY`` from the environment. See ``.env.example``.
"""

from __future__ import annotations

from trajaudit.core.verdict import SemanticVerdict
from trajaudit.layer3_semantic.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI Chat Completions / Responses-backed judge."""

    name = "openai"

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        max_tokens: int = 2048,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens

    def query(self, messages: list[dict[str, str]]) -> SemanticVerdict:
        raise NotImplementedError("Phase 4: implement OpenAI Responses call.")
