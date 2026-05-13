"""Abstract base class for Layer 3 LLM providers.

Every concrete provider — vLLM, Anthropic, OpenAI — implements the
same minimal contract: take a list of chat-style messages, return a
parsed :class:`~trajaudit.core.verdict.SemanticVerdict`. Implementations
read credentials from environment variables, never from constructor
arguments that would surface in shell history.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from trajaudit.core.verdict import SemanticVerdict


class LLMProvider(ABC):
    """Common interface every Layer 3 backend implements."""

    #: Stable provider name used in escalation provenance.
    name: str

    @abstractmethod
    def query(self, messages: list[dict[str, str]]) -> SemanticVerdict:
        """Send the messages to the provider and return a parsed verdict."""


__all__ = ["LLMProvider"]
