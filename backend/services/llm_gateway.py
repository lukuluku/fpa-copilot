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

        # Sonnet 5 does not support temperature parameter; needs more tokens for thinking
        if "sonnet" in model.lower():
            max_tokens = max(max_tokens, 16000)  # Sonnet needs room for extended thinking

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if "sonnet" not in model.lower():
            kwargs["temperature"] = temperature

        message = self.client.messages.create(**kwargs)

        # Handle extended thinking (ThinkingBlock) in Sonnet 5
        text_content = None
        for block in message.content:
            if type(block).__name__ == 'TextBlock':
                text_content = block.text
                break

        if text_content is None:
            # Fallback: try to get first text-like attribute
            if message.content and hasattr(message.content[0], 'text'):
                text_content = message.content[0].text
            else:
                raise ValueError(f"No text content in message response. Content types: {[type(b).__name__ for b in message.content]}")

        return LLMResponse(
            text=text_content,
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
        """Synchronous wrapper — handles both running and non-running event loops."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        try:
            # Check if event loop is already running (e.g., in FastAPI context)
            asyncio.get_running_loop()
            # If we get here, a loop is running, so use ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(
                    asyncio.run,
                    self.complete(system, user, temperature, max_tokens, model_override)
                ).result()
        except RuntimeError:
            # No running loop, safe to use run_until_complete
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
