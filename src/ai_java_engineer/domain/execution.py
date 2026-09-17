"""Execution state and budget models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Lifecycle statuses for an execution run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class ExecutionBudget(BaseModel):
    """Resource ceilings for an autonomous run to prevent runaway costs."""
    max_total_tokens: int = Field(default=250_000, description="Max prompt + completion tokens")
    max_model_calls: int = Field(default=40, description="Max LLM API calls")
    max_debug_iterations: int = Field(default=3, description="Max self-healing debug attempts")
    max_runtime_seconds: int = Field(default=1800, description="Max run time before timeout")


class FailureFingerprint(BaseModel):
    """Fingerprint identifying a specific error to detect repetitive fix loops."""
    fingerprint_hash: str = Field(description="SHA-256 hash of normalized error message and location")
    error_type: str = Field(description="COMPILATION_ERROR, TEST_FAILURE, RUNTIME_ERROR")
    file: str | None = Field(default=None)
    line: int | None = Field(default=None)
    summary: str = Field(description="Short synopsis of the error")


class BuildResult(BaseModel):
    """Result of a Maven compile/package execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str = ""
    duration_ms: int = 0
    error_summary: str | None = None
    fingerprint: FailureFingerprint | None = None


class TestCaseResult(BaseModel):
    """Result of an individual JUnit test case."""
    __test__ = False
    classname: str
    name: str
    time: float = 0.0
    status: str = "PASSED"  # PASSED, FAILED, ERROR, SKIPPED
    failure_message: str | None = None
    stacktrace: str | None = None


class TestResult(BaseModel):
    """Aggregated results from a Maven Surefire test execution."""
    __test__ = False
    passed: bool
    total: int
    passed_count: int
    failed_count: int
    skipped_count: int = 0
    duration_ms: int = 0
    cases: list[TestCaseResult] = Field(default_factory=list)
    stdout_ref: str = ""
    fingerprint: FailureFingerprint | None = None


class ExecutionState(BaseModel):
    """Snapshot of run execution state."""
    execution_id: str
    status: RunStatus = RunStatus.PENDING
    iteration: int = 0
    max_iterations: int = 3
    tokens_used: int = 0
    model_calls_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
