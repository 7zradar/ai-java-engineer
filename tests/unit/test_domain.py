"""Unit tests for domain models and data contracts."""

import pytest
from pydantic import ValidationError

from ai_java_engineer.domain.architecture import EndpointSpec
from ai_java_engineer.domain.execution import ExecutionBudget, TestCaseResult, TestResult
from ai_java_engineer.domain.requirement import AcceptanceCriterion, ProductSpec, UserStory


def test_execution_budget_defaults():
    budget = ExecutionBudget()
    assert budget.max_total_tokens == 250_000
    assert budget.max_model_calls == 40
    assert budget.max_debug_iterations == 3


def test_product_spec_creation():
    spec = ProductSpec(
        title="Sample Feature",
        summary="Summary of feature",
        user_stories=[
            UserStory(
                id="US-1",
                title="Story 1",
                as_a="User",
                i_want="Feature",
                so_that="Benefit",
            )
        ],
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                scenario="Happy path",
                given="State A",
                when="Action B",
                then="Result C",
            )
        ],
    )
    assert spec.title == "Sample Feature"
    assert len(spec.user_stories) == 1
    assert spec.acceptance_criteria[0].scenario == "Happy path"


def test_endpoint_spec_validation():
    endpoint = EndpointSpec(
        method="GET",
        path="/api/v1/orders",
        description="List orders",
        response_dto="OrderDTO",
    )
    assert endpoint.status_code == 200

    # Invalid HTTP method should raise ValidationError
    with pytest.raises(ValidationError):
        EndpointSpec(
            method="INVALID_METHOD",  # type: ignore
            path="/api/v1/orders",
            description="test",
            response_dto="OrderDTO",
        )


def test_test_result_aggregation():
    tr = TestResult(
        passed=True,
        total=2,
        passed_count=2,
        failed_count=0,
        cases=[
            TestCaseResult(classname="TestA", name="m1", time=0.01, status="PASSED"),
            TestCaseResult(classname="TestA", name="m2", time=0.02, status="PASSED"),
        ],
    )
    assert tr.passed is True
    assert tr.total == 2
