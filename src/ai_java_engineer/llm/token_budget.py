"""Execution token and financial budget accounting."""

from ai_java_engineer.domain.execution import ExecutionBudget
from ai_java_engineer.infrastructure.errors import BudgetExceededError
from ai_java_engineer.llm.base import TokenUsage


class TokenBudgetTracker:
    """Tracks token accumulation, request counts, and enforces limits."""

    def __init__(self, budget: ExecutionBudget | None = None):
        self.budget = budget or ExecutionBudget()
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0
        self.model_calls_count: int = 0
        self.total_cost_usd: float = 0.0

    def record_usage(self, usage: TokenUsage) -> None:
        """Records token usage and asserts against budget ceilings."""
        self.model_calls_count += 1
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.total_cost_usd += usage.estimated_cost_usd

        # Assert budget guardrails
        if self.model_calls_count > self.budget.max_model_calls:
            raise BudgetExceededError(
                f"Model call budget exceeded: {self.model_calls_count} > {self.budget.max_model_calls}",
                details={"calls": self.model_calls_count, "limit": self.budget.max_model_calls},
            )

        if self.total_tokens > self.budget.max_total_tokens:
            raise BudgetExceededError(
                f"Total token budget exceeded: {self.total_tokens} > {self.budget.max_total_tokens}",
                details={"tokens": self.total_tokens, "limit": self.budget.max_total_tokens},
            )

    def summary(self) -> dict:
        return {
            "calls": self.model_calls_count,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
        }
