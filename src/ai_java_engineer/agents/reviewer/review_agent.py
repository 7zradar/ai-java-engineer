"""Review Agent: performs contract-driven verification comparing diff against specs and test evidence."""

from ai_java_engineer.domain.architecture import ArchitectureSpec
from ai_java_engineer.domain.artifact import ReviewResult, SecurityResult
from ai_java_engineer.domain.execution import TestResult
from ai_java_engineer.domain.requirement import ProductSpec
from ai_java_engineer.llm.base import ModelProvider, ModelRequest


class ReviewAgent:
    """Evaluates whether the implementation fulfills all product and architecture requirements."""

    SYSTEM_PROMPT = (
        "You are an Engineering Reviewer evaluating pull requests. "
        "Review the generated git diff against the Product Specification, Architecture Blueprint, "
        "and Test Execution results. Return a structured ReviewResult with discrete checklist items."
    )

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def execute(
        self,
        product_spec: ProductSpec,
        arch_spec: ArchitectureSpec,
        git_diff: str,
        test_result: TestResult | None,
        security_result: SecurityResult | None,
    ) -> ReviewResult:
        test_passed = test_result.passed if test_result else False
        security_passed = security_result.passed if security_result else False

        prompt = (
            f"Product: {product_spec.title}\n"
            f"Acceptance Criteria count: {len(product_spec.acceptance_criteria)}\n"
            f"Architecture: {arch_spec.summary}\n"
            f"Test Evidence: Passed={test_passed}, Cases={test_result.total if test_result else 0}\n"
            f"Security Evidence: Passed={security_passed}\n\n"
            f"Git Diff:\n{git_diff[:20000]}\n\n"
            f"Provide a structured code review verdict."
        )

        request = ModelRequest(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.05,
        )

        result, _ = await self.provider.generate_structured(request, ReviewResult)
        return result
