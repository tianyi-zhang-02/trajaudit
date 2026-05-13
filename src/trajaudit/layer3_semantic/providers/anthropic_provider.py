"""Anthropic Claude judge provider.

Frontier tier in the Layer 3 escalation chain. Uses the official
``anthropic`` SDK and the Messages API. The default model target is
the latest Claude Sonnet for cost/quality balance, with the option to
switch to a more capable model for the final tier.

Reads ``ANTHROPIC_API_KEY`` from the environment; the constructor
never accepts the key as a string argument that could surface in
shell history. See ``.env.example``.
"""

from __future__ import annotations

from trajaudit.core.verdict import SemanticVerdict
from trajaudit.layer3_semantic.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude-backed judge."""

    name = "anthropic"

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens

    def query(self, messages: list[dict[str, str]]) -> SemanticVerdict:
        raise NotImplementedError("Phase 4: implement Anthropic Messages call.")
