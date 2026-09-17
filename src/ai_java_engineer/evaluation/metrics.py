"""Evaluation metrics and standardized error taxonomy for AI engineering benchmarks."""

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standardized AI Engineering error taxonomy."""
    E001 = "E001: Requirement misunderstanding"
    E002 = "E002: Architecture violation"
    E003 = "E003: Compilation failure"
    E004 = "E004: Functional test failure"
    E005 = "E005: Test generation failure"
    E006 = "E006: Regression on existing codebase"
    E007 = "E007: Security policy violation"
    E008 = "E008: Context retrieval failure"
    E009 = "E009: Tool execution error"
    E010 = "E010: Hallucinated dependency"


class BenchmarkTask(BaseModel):
    """Dataset task specification."""
    task_id: str
    title: str
    requirement: str
    category: str = "FEATURE"  # CRUD, VALIDATION, INTEGRATION, BUG_FIX
    visible_tests: list[str] = Field(default_factory=list)
    hidden_tests: list[str] = Field(default_factory=list)
    expected_classes: list[str] = Field(default_factory=list)


class TaskEvaluationResult(BaseModel):
    task_id: str
    build_passed: bool
    visible_tests_passed: bool
    hidden_tests_passed: bool
    error_code: ErrorCode | None = None
    duration_ms: int
    cost_usd: float


class BenchmarkReport(BaseModel):
    """Consolidated benchmark evaluation summary."""
    total_tasks: int
    build_success_rate: float
    visible_test_pass_rate: float
    hidden_test_pass_rate: float
    average_cost_usd: float
    average_duration_seconds: float
    error_distribution: dict[str, int] = Field(default_factory=dict)
    task_results: list[TaskEvaluationResult] = Field(default_factory=list)
