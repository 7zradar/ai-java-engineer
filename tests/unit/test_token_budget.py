"""Unit tests for token accounting and budget enforcement."""

import pytest

from ai_java_engineer.domain.execution import ExecutionBudget
from ai_java_engineer.infrastructure.errors import BudgetExceededError
from ai_java_engineer.llm.base import TokenUsage
from ai_java_engineer.llm.token_budget import TokenBudgetTracker


def test_token_budget_normal_tracking():
    budget = ExecutionBudget(max_total_tokens=1000, max_model_calls=5)
    tracker = TokenBudgetTracker(budget)

    tracker.record_usage(
        TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, estimated_cost_usd=0.001)
    )
    assert tracker.total_tokens == 150
    assert tracker.model_calls_count == 1
    assert tracker.total_cost_usd == 0.001


def test_token_budget_call_limit_exceeded():
    budget = ExecutionBudget(max_total_tokens=100_000, max_model_calls=2)
    tracker = TokenBudgetTracker(budget)

    tracker.record_usage(TokenUsage(total_tokens=10))
    tracker.record_usage(TokenUsage(total_tokens=10))

    with pytest.raises(BudgetExceededError):
        tracker.record_usage(TokenUsage(total_tokens=10))


def test_token_budget_token_limit_exceeded():
    budget = ExecutionBudget(max_total_tokens=500, max_model_calls=10)
    tracker = TokenBudgetTracker(budget)

    tracker.record_usage(TokenUsage(total_tokens=400))
    with pytest.raises(BudgetExceededError):
        tracker.record_usage(TokenUsage(total_tokens=150))
