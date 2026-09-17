"""Architect Agent: designs technical blueprint and ADRs for Java/Spring Boot."""

from ai_java_engineer.domain.architecture import ArchitectureSpec
from ai_java_engineer.domain.requirement import ProductSpec
from ai_java_engineer.llm.base import ModelProvider, ModelRequest


class ArchitectAgent:
    """Designs Spring Boot components, REST endpoints, and JPA entities based on ProductSpec."""

    SYSTEM_PROMPT = (
        "You are a Principal Java / Spring Boot Architect. "
        "Analyze the product requirements and repository context to design an idiomatic, "
        "layered Spring Boot architecture (Controller, Service, Repository, DTO). "
        "Explicitly document endpoints, entities, dependencies, and Architecture Decision Records (ADR)."
    )

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def execute(self, product_spec: ProductSpec, repository_context: str) -> ArchitectureSpec:
        prompt = (
            f"Product Specification:\n"
            f"Title: {product_spec.title}\n"
            f"Summary: {product_spec.summary}\n"
            f"Acceptance Criteria Count: {len(product_spec.acceptance_criteria)}\n\n"
            f"Repository Context:\n{repository_context}\n\n"
            f"Design the Architecture Specification for Spring Boot 3+ / Java 21."
        )

        request = ModelRequest(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.1,
        )

        spec, _ = await self.provider.generate_structured(request, ArchitectureSpec)
        return spec
