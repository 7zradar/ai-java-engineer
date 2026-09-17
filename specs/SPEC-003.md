# SPEC-003: LLM Provider Abstraction

## Objective
Provide a vendor-neutral, protocol-based interface for Large Language Models supporting structured generation, token accounting, retries with exponential backoff, and budget guards.

## Context
Directly coupling business logic to OpenAI, Gemini, or Anthropic clients creates vendor lock-in and prevents offline testing. The platform requires a unified protocol `ModelProvider`.

## Scope
- `ModelProvider` Protocol.
- `ModelRequest` and `ModelResponse` structures.
- Structured output enforcement using Pydantic schemas.
- Implementations: `MockProvider`, `GeminiProvider`, `OpenAIProvider`, `AnthropicProvider`.
- `TokenBudgetTracker` for hard limits on execution cost.

## Non-scope
- Local model fine-tuning or quantization pipelines.

## Functional Requirements
- FR-3.1: Support typed structured output extraction returning validated Pydantic instances.
- FR-3.2: Enforce token and request counts against `ExecutionBudget`.
- FR-3.3: Automatically retry transient network errors (HTTP 429, 503) using Tenacity with jittered exponential backoff.

## Non-functional Requirements
- Deterministic behavior in `MockProvider` for test repeatability.
- Asynchronous non-blocking I/O across all providers.

## Interfaces
```python
class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse:
        ...

    async def generate_structured(
        self, request: ModelRequest, response_model: type[T]
    ) -> T:
        ...
```

## Security Considerations
Provider implementations must never log raw API keys. Headers containing authorization tokens are masked.

## Observability
Tracks prompt tokens, completion tokens, latency (ms), and estimated USD cost per call.

## Failure Handling
Rate limits trigger exponential backoff. Exceeding token budgets raises `BudgetExceededError`.

## Acceptance Criteria
- `MockProvider` returns canned or synthetic structured objects reliably.
- `TokenBudgetTracker` interrupts execution when token limit is breached.

## Tests
- `test_mock_provider_structured_output`
- `test_token_budget_exceeded_raises_error`
- `test_provider_retry_policy`

## Definition of Done
Vendor abstraction verified with at least one mock and one real provider schema compatibility.
