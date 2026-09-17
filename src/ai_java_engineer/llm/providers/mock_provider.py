"""Deterministic Mock Provider for unit testing and offline execution."""

from typing import Any, TypeVar

from pydantic import BaseModel

from ai_java_engineer.domain.architecture import (
    ArchitectureDecision,
    ArchitectureSpec,
    ComponentSpec,
    EndpointSpec,
    EntitySpec,
)
from ai_java_engineer.domain.artifact import (
    CodePlan,
    FileAction,
    ReviewChecklistItem,
    ReviewResult,
    SecurityResult,
)
from ai_java_engineer.domain.requirement import (
    AcceptanceCriterion,
    ProductSpec,
    UserStory,
)
from ai_java_engineer.llm.base import ModelProvider, ModelRequest, ModelResponse, TokenUsage

T = TypeVar("T", bound=BaseModel)


class MockProvider(ModelProvider):
    """Deterministic model provider used for unit testing, offline verification, and benchmarks."""

    def __init__(self, canned_responses: dict[str, Any] | None = None):
        self.canned_responses = canned_responses or {}
        self.call_history: list[ModelRequest] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.call_history.append(request)
        content = "Mock LLM text response"
        return ModelResponse(
            content=content,
            usage=TokenUsage(prompt_tokens=150, completion_tokens=50, total_tokens=200, estimated_cost_usd=0.0004),
            latency_ms=12,
        )

    async def generate_structured(
        self, request: ModelRequest, response_model: type[T]
    ) -> tuple[T, ModelResponse]:
        self.call_history.append(request)
        model_name = response_model.__name__

        if model_name in self.canned_responses:
            instance = response_model.model_validate(self.canned_responses[model_name])
            return instance, ModelResponse(
                content=instance.model_dump_json(),
                usage=TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300, estimated_cost_usd=0.0006),
                latency_ms=15,
            )

        # Generate sensible deterministic synthetic data based on requested model
        instance: Any
        if response_model is ProductSpec:
            instance = ProductSpec(
                title="Customer Order History API",
                summary="Provide paginated order history endpoint for customers",
                user_stories=[
                    UserStory(
                        id="US-001",
                        title="View past orders",
                        as_a="Customer",
                        i_want="to retrieve my order history with status filters",
                        so_that="I can track past purchases easily",
                    )
                ],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-001",
                        scenario="Retrieve customer orders with valid ID",
                        given="A customer with existing orders",
                        when="GET /api/v1/customers/101/orders is invoked",
                        then="Returns HTTP 200 with list of orders",
                    )
                ],
                business_rules=["Only return orders belonging to the authenticated customer ID"],
                edge_cases=["Customer with zero orders returns empty list with 200 OK"],
                assumptions=["Spring Boot 3.3+ and Java 21 environment"],
                unresolved_questions=[],
            )
        elif response_model is ArchitectureSpec:
            instance = ArchitectureSpec(
                summary="Add OrderController endpoint and OrderService business logic",
                packages_to_modify=["com.example.demo.controller", "com.example.demo.service"],
                components=[
                    ComponentSpec(
                        package="com.example.demo.controller",
                        name="OrderController",
                        component_type="CONTROLLER",
                        description="REST controller exposing customer order endpoints",
                        dependencies=["OrderService"],
                    ),
                    ComponentSpec(
                        package="com.example.demo.service",
                        name="OrderService",
                        component_type="SERVICE",
                        description="Business logic handling order filtering",
                        dependencies=["OrderRepository"],
                    ),
                ],
                endpoints=[
                    EndpointSpec(
                        method="GET",
                        path="/api/v1/customers/{id}/orders",
                        description="Fetch paginated order history",
                        response_dto="OrderResponseDTO",
                        status_code=200,
                    )
                ],
                entities=[
                    EntitySpec(
                        name="Order",
                        table_name="orders",
                        fields={"id": "Long", "customerId": "Long", "status": "String", "amount": "BigDecimal"},
                    )
                ],
                dependencies_needed=[],
                decisions=[
                    ArchitectureDecision(
                        id="ADR-001",
                        title="Use Spring Data JPA derived queries",
                        context="Need efficient filtering by customer ID",
                        decision="Implement findByCustomerId in OrderRepository",
                        consequences="Avoids custom SQL and ensures type safety",
                    )
                ],
            )
        elif response_model is CodePlan:
            java_controller = (
                "package com.example.demo.controller;\n\n"
                "import org.springframework.web.bind.annotation.*;\n"
                "import org.springframework.http.ResponseEntity;\n"
                "import java.util.List;\n\n"
                "@RestController\n"
                "@RequestMapping(\"/api/v1/customers\")\n"
                "public class OrderController {\n"
                "    @GetMapping(\"/{id}/orders\")\n"
                "    public ResponseEntity<List<String>> getOrders(@PathVariable Long id) {\n"
                "        return ResponseEntity.ok(List.of(\"ORDER-1001\", \"ORDER-1002\"));\n"
                "    }\n"
                "}\n"
            )
            java_test = (
                "package com.example.demo.controller;\n\n"
                "import org.junit.jupiter.api.Test;\n"
                "import org.springframework.http.ResponseEntity;\n"
                "import java.util.List;\n"
                "import static org.junit.jupiter.api.Assertions.*;\n\n"
                "class OrderControllerTest {\n"
                "    @Test\n"
                "    void testGetOrdersSuccess() {\n"
                "        OrderController controller = new OrderController();\n"
                "        ResponseEntity<List<String>> response = controller.getOrders(101L);\n"
                "        assertEquals(200, response.getStatusCode().value());\n"
                "        assertFalse(response.getBody().isEmpty());\n"
                "    }\n"
                "}\n"
            )
            instance = CodePlan(
                summary="Implement OrderController and OrderControllerTest",
                actions=[
                    FileAction(
                        path="src/main/java/com/example/demo/controller/OrderController.java",
                        action="CREATE",
                        content=java_controller,
                        description="REST Controller endpoint",
                    ),
                    FileAction(
                        path="src/test/java/com/example/demo/controller/OrderControllerTest.java",
                        action="CREATE",
                        content=java_test,
                        description="Unit test verifying 200 OK response",
                    ),
                ],
            )
        elif response_model is SecurityResult:
            instance = SecurityResult(
                passed=True,
                has_critical=False,
                findings=[],
            )
        elif response_model is ReviewResult:
            instance = ReviewResult(
                verdict="APPROVED",
                score=0.95,
                summary="Implementation satisfies requirements with test coverage",
                checklist=[
                    ReviewChecklistItem(name="Acceptance Criteria Covered", passed=True, details="AC-001 verified"),
                    ReviewChecklistItem(name="Spring Architecture Followed", passed=True, details="Layering conforms"),
                ],
                required_changes=[],
            )
        else:
            instance = response_model.model_validate({})

        return instance, ModelResponse(
            content=instance.model_dump_json(),
            usage=TokenUsage(prompt_tokens=250, completion_tokens=150, total_tokens=400, estimated_cost_usd=0.0008),
            latency_ms=20,
        )
