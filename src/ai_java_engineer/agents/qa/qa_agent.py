"""QA & Test Automation Agent: generates independent edge case, negative, and integration tests."""

from ai_java_engineer.domain.architecture import ArchitectureSpec
from ai_java_engineer.domain.artifact import CodePlan
from ai_java_engineer.domain.requirement import ProductSpec
from ai_java_engineer.llm.base import ModelProvider, ModelRequest


class QAAgent:
    """Specialized Subagent responsible for independent Quality Assurance.
    Generates negative scenarios, boundary checks, and HTTP error assertions (400, 404, 500).
    """

    SYSTEM_PROMPT = (
        "You are an Elite Java QA Automation & Test Architect specializing in JUnit 5, AssertJ, and Mockito. "
        "Your mission is to aggressively stress-test the implementation: "
        "1. Negative tests for invalid inputs, missing required fields, and boundary values (HTTP 400). "
        "2. Resource not found scenarios (HTTP 404). "
        "3. Concurrency and empty data sets (e.g. empty lists, null handling). "
        "4. Mocking downstream failures and timeout scenarios. "
        "Output a structured CodePlan containing exclusively test classes under src/test/java/."
    )

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def execute(
        self,
        product_spec: ProductSpec,
        arch_spec: ArchitectureSpec,
        code_plan: CodePlan,
    ) -> CodePlan:
        implemented_files = [a.path for a in code_plan.actions]
        prompt = (
            f"Feature Title: {product_spec.title}\n"
            f"Acceptance Criteria:\n"
        )
        for ac in product_spec.acceptance_criteria:
            prompt += f"- [{ac.id}] Given: {ac.given}, When: {ac.when}, Then: {ac.then}\n"

        prompt += "\nEdge Cases to Cover:\n"
        for ec in product_spec.edge_cases:
            prompt += f"- {ec}\n"

        prompt += (
            f"\nEndpoints under test: {[f'{e.method} {e.path}' for e in arch_spec.endpoints]}\n"
            f"Implemented Classes: {implemented_files}\n\n"
            "Generate comprehensive JUnit 5 QA test suites covering all edge cases and negative validations."
        )

        request = ModelRequest(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.1,
        )

        qa_plan, _ = await self.provider.generate_structured(request, CodePlan)
        return qa_plan
