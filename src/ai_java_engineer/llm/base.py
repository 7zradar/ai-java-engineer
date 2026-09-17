"""Vendor-neutral LLM provider protocol and schemas."""

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    """Token consumption statistics for a single request."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ModelRequest(BaseModel):
    """Unified request schema sent to any LLM provider."""
    prompt: str
    system_instruction: str = ""
    temperature: float = 0.2
    max_tokens: int | None = None
    stop_sequences: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    """Unified response schema returned by any LLM provider."""
    content: str
    raw_response: dict[str, Any] = Field(default_factory=dict)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = 0


class ModelProvider(Protocol):
    """Abstract protocol for all model providers (OpenAI, Gemini, Anthropic, Mock)."""

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generates text from a model request."""
        ...

    async def generate_structured(
        self, request: ModelRequest, response_model: type[T]
    ) -> tuple[T, ModelResponse]:
        """Generates and validates a structured Pydantic object."""
        ...
