"""Coding Agent: generates Java 21 / Spring Boot files and JUnit 5 test suites."""

from ai_java_engineer.domain.architecture import ArchitectureSpec
from ai_java_engineer.domain.artifact import CodePlan
from ai_java_engineer.domain.requirement import ProductSpec
from ai_java_engineer.llm.base import ModelProvider, ModelRequest


class CodingAgent:
    """Generates production-grade Spring Boot components and corresponding JUnit 5 tests."""

    SYSTEM_PROMPT = (
        "You are an Expert Java 21 / Spring Boot 3 Software Engineer. "
        "Generate idiomatic, clean code conforming strictly to the provided Architecture Specification. "
        "Every feature class must have a corresponding JUnit 5 test class using Mockito / AssertJ. "
        "Do not write conversational explanations; output exclusively a structured CodePlan with file paths and full contents."
    )

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def execute(
        self,
        product_spec: ProductSpec,
        arch_spec: ArchitectureSpec,
        repository_context: str,
    ) -> CodePlan:
        prompt = (
            f"Product Title: {product_spec.title}\n"
            f"Acceptance Criteria:\n"
        )
        for ac in product_spec.acceptance_criteria:
            prompt += f"- [{ac.id}] Given: {ac.given}, When: {ac.when}, Then: {ac.then}\n"

        prompt += (
            f"\nArchitecture Summary: {arch_spec.summary}\n"
            f"Components to generate: {[c.name for c in arch_spec.components]}\n"
            f"Endpoints: {[f'{e.method} {e.path}' for e in arch_spec.endpoints]}\n\n"
            f"Repository Context:\n{repository_context}\n\n"
            f"Generate the complete CodePlan including Java sources and JUnit 5 tests."
        )

        request = ModelRequest(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.1,
        )

        plan, _ = await self.provider.generate_structured(request, CodePlan)
        return plan
