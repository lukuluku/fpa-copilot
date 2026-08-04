"""
LLM abstraction layer — unified interface for all agent LLM calls.
Supports multiple providers (Anthropic, Azure OpenAI, etc.) via env vars.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from anthropic import Anthropic


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    text: str
    model: str
    stop_reason: str
    input_tokens: int
    output_tokens: int


class LLMGateway(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model_override: str | None = None,
    ) -> LLMResponse:
        """Send a prompt to the LLM and return the response."""
        pass

    def sync_complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model_override: str | None = None,
    ) -> LLMResponse:
        """Synchronous wrapper for async complete()."""
        raise NotImplementedError("Override in subclass")


class AnthropicGateway(LLMGateway):
    """Anthropic Claude API gateway."""

    DEFAULT_MODELS = {
        "router": "claude-haiku-4-5-20251001",
        "retrieval": "claude-haiku-4-5-20251001",
        "drafter_qa": "claude-haiku-4-5-20251001",
    }

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=api_key)

        # Allow model override via env vars (for testing/evals)
        for role in self.DEFAULT_MODELS.keys():
            env_var = f"LLM_MODEL_{role.upper()}"
            if os.getenv(env_var):
                self.DEFAULT_MODELS[role] = os.getenv(env_var)

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model_override: str | None = None,
    ) -> LLMResponse:
        """Call Anthropic API (sync implementation for Phase 2)."""
        model = model_override or self.DEFAULT_MODELS.get("drafter_qa", "claude-haiku-4-5-20251001")

        message = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        return LLMResponse(
            text=message.content[0].text,
            model=message.model,
            stop_reason=message.stop_reason,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

    def sync_complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model_override: str | None = None,
    ) -> LLMResponse:
        """Synchronous wrapper — just calls the async method directly in Phase 2."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.complete(system, user, temperature, max_tokens, model_override)
        )


def get_llm_gateway() -> LLMGateway:
    """Factory function to get the appropriate LLM gateway based on env vars."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic":
        return AnthropicGateway()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
