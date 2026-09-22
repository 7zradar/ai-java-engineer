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
                title="API de Historial de Pedidos de Clientes",
                summary="Proveer un endpoint REST paginado para consultar el historial de pedidos de clientes con filtros de estado.",
                user_stories=[
                    UserStory(
                        id="US-001",
                        title="Consultar pedidos anteriores",
                        as_a="Cliente registrado",
                        i_want="consultar mi historial de pedidos con filtros por estado (PENDING, SHIPPED)",
                        so_that="pueda realizar seguimiento a mis compras previas",
                    )
                ],
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id="AC-001",
                        scenario="Consultar pedidos con ID de cliente válido",
                        given="Un cliente registrado con pedidos existentes en la base de datos",
                        when="Se invoca la petición GET /api/v1/customers/101/orders",
                        then="El sistema responde con código HTTP 200 y la lista paginada de pedidos",
                    ),
                    AcceptanceCriterion(
                        id="AC-002",
                        scenario="Cliente sin compras registradas",
                        given="Un cliente registrado que no posee órdenes previas",
                        when="Se invoca la petición GET /api/v1/customers/102/orders",
                        then="El sistema responde con código HTTP 200 y una lista vacía",
                    ),
                    AcceptanceCriterion(
                        id="AC-003",
                        scenario="Identificador de cliente inválido",
                        given="Un identificador de cliente menor a 1 o malformado",
                        when="Se invoca la petición GET /api/v1/customers/-1/orders",
                        then="El sistema responde con código HTTP 400 Bad Request y formato ErrorResponseDTO",
                    ),
                ],
                business_rules=[
                    "Solo se deben retornar pedidos pertenecientes al cliente autenticado",
                    "El tamaño de página por defecto debe ser de 10 registros",
                    "Todos los errores deben utilizar el formato corporativo ErrorResponseDTO",
                ],
                edge_cases=[
                    "Cliente con cero pedidos retorna lista vacía con HTTP 200 OK",
                    "Parámetros de paginación inválidos deben retornar HTTP 400 Bad Request",
                    "Filtro de estado inexistente debe ser rechazado con HTTP 400 Bad Request",
                ],
                assumptions=["Entorno de ejecución con Spring Boot 3.3+ y Java 21"],
                unresolved_questions=[],
            )
        elif response_model is ArchitectureSpec:
            instance = ArchitectureSpec(
                summary="Diseño de controlador REST OrderController, capa de servicio OrderService y repositorio Spring Data JPA",
                packages_to_modify=["com.example.demo.controller", "com.example.demo.service"],
                components=[
                    ComponentSpec(
                        package="com.example.demo.controller",
                        name="OrderController",
                        component_type="CONTROLLER",
                        description="Controlador REST que expone los endpoints de pedidos de clientes",
                        dependencies=["OrderService"],
                    ),
                    ComponentSpec(
                        package="com.example.demo.service",
                        name="OrderService",
                        component_type="SERVICE",
                        description="Lógica de negocio para filtrado y paginación de pedidos",
                        dependencies=["OrderRepository"],
                    ),
                ],
                endpoints=[
                    EndpointSpec(
                        method="GET",
                        path="/api/v1/customers/{id}/orders",
                        description="Consulta paginada del historial de pedidos",
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
                        title="Uso de métodos derivados en Spring Data JPA",
                        context="Se requiere un filtrado eficiente por identificador de cliente",
                        decision="Implementar findByCustomerId en OrderRepository",
                        consequences="Garantiza seguridad de tipos y evita consultas SQL manuales propensas a errores",
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
                summary="Implementación de OrderController y suite de pruebas unitarias OrderControllerTest",
                actions=[
                    FileAction(
                        path="src/main/java/com/example/demo/controller/OrderController.java",
                        action="CREATE",
                        content=java_controller,
                        description="Controlador REST para pedidos de clientes",
                    ),
                    FileAction(
                        path="src/test/java/com/example/demo/controller/OrderControllerTest.java",
                        action="CREATE",
                        content=java_test,
                        description="Prueba unitaria verificando respuesta HTTP 200 OK",
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
                summary="La implementación cumple plenamente con los criterios de aceptación y los estándares de arquitectura Spring Boot",
                checklist=[
                    ReviewChecklistItem(name="Criterios de Aceptación Cubiertos", passed=True, details="AC-001, AC-002 y AC-003 validados con tests"),
                    ReviewChecklistItem(name="Arquitectura Spring Boot Respetada", passed=True, details="Separación limpia de capas Controller, Service y Repository"),
                    ReviewChecklistItem(name="Seguridad y OWASP", passed=True, details="Sin vulnerabilidades de inyección SQL ni credenciales en código"),
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
