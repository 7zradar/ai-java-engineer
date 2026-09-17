"""Engineering state typed contract for LangGraph orchestration."""

from typing import TypedDict

from ai_java_engineer.domain.architecture import ArchitectureSpec
from ai_java_engineer.domain.artifact import (
    CodePlan,
    PullRequestPayload,
    ReviewResult,
    SecurityResult,
)
from ai_java_engineer.domain.execution import BuildResult, RunStatus, TestResult
from ai_java_engineer.domain.requirement import ProductSpec, RequirementSpec
from ai_java_engineer.retrieval.repository_map import RepositoryMap


class EngineeringState(TypedDict, total=False):
    """Strongly typed state dictionary passed across LangGraph nodes."""

    # Identity and Governance
    execution_id: str
    status: RunStatus
    iteration: int
    max_iterations: int
    human_approved: bool
    escalation_reason: str | None

    # Workspace & Core Inputs
    workspace_path: str
    requirement: RequirementSpec
    repo_map: RepositoryMap | None
    repository_context: str | None

    # Specifications
    product_spec: ProductSpec | None
    architecture_spec: ArchitectureSpec | None

    # Artifacts & Modifications
    code_plan: CodePlan | None
    changed_files: list[str]
    git_diff: str | None

    # Verification & Quality Results
    build_result: BuildResult | None
    test_result: TestResult | None
    security_result: SecurityResult | None
    review_result: ReviewResult | None

    # Final Delivery
    pr_payload: PullRequestPayload | None
