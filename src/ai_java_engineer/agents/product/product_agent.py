"""Product Agent: analyzes raw requirements and produces structured ProductSpec."""

from ai_java_engineer.domain.requirement import ProductSpec, RequirementSpec
from ai_java_engineer.llm.base import ModelProvider, ModelRequest


class ProductAgent:
    """Refines ambiguous user requirements into testable, structured specifications."""

    SYSTEM_PROMPT = (
        "You are a Senior Technical Product Manager for an enterprise software system. "
        "Your role is to transform natural language feature requests into a rigorous, "
        "strongly typed Product Specification with user stories, Given-When-Then acceptance criteria, "
        "business rules, and edge cases. Do not generate code. "
        "Always write the user stories (como, quiero, para), acceptance criteria (escenario, dado, cuando, entonces), "
        "business rules, and summaries in Spanish, keeping standard technical software terminology in English "
        "(e.g., endpoints, Spring Boot, DTOs, HTTP status codes, REST)."
    )


    def __init__(self, provider: ModelProvider):
        self.provider = provider

    async def execute(self, req: RequirementSpec) -> ProductSpec:
        prompt = (
            f"Feature Title: {req.title}\n"
            f"Raw Requirement:\n{req.raw_text}\n\n"
            f"Target Repository: {req.target_repository}\n"
            f"Constraints: {', '.join(req.constraints) if req.constraints else 'None'}\n\n"
            f"Produce a complete, structured Product Specification."
        )

        request = ModelRequest(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.1,
        )

        spec, _ = await self.provider.generate_structured(request, ProductSpec)
        return spec
