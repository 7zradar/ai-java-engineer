# SPEC-002: Domain & Execution Model

## Objective
Define the pure, immutable, contract-driven domain entities and execution state schemas for the agentic engineering platform.

## Context
Agents must communicate through strongly typed contracts rather than unstructured, free-form text. Every state transition, artifact, and tool output must validate against explicit Pydantic v2 models.

## Scope
- `ExecutionId`, `RunStatus`, `ExecutionBudget`.
- `RequirementSpec`, `UserStory`, `AcceptanceCriterion`, `BusinessRule`.
- `ProductSpec`, `ArchitectureSpec`, `ComponentSpec`, `EndpointSpec`, `EntitySpec`.
- `BuildResult`, `TestResult`, `SecurityResult`, `ReviewResult`.
- `ExecutionState` definition.

## Non-scope
- Database serialization tables (handled in infrastructure).

## Functional Requirements
- FR-2.1: Domain models must validate required fields upon instantiation.
- FR-2.2: Models must support schema export for LLM structured output enforcement.
- FR-2.3: State transitions must maintain historical audit metadata.

## Non-functional Requirements
- Zero external runtime dependencies outside `pydantic`.
- Memory efficient serialization and immutability where applicable.

## Architecture
- `ai_java_engineer.domain.execution`
- `ai_java_engineer.domain.requirement`
- `ai_java_engineer.domain.architecture`
- `ai_java_engineer.domain.artifact`

## Schemas
```python
class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"

class ExecutionBudget(BaseModel):
    max_total_tokens: int = 250_000
    max_model_calls: int = 40
    max_debug_iterations: int = 3
    max_runtime_seconds: int = 1800
```

## Security Considerations
Validate string lengths and sanitize characters in user-provided requirement titles and story descriptions.

## Observability
Execution state tracks total tokens consumed, model invocation counts, and step latencies.

## Failure Handling
Schema validation errors raise `ValidationError` with detailed field paths.

## Acceptance Criteria
- All domain models serialize to/from JSON cleanly.
- Immutability checks and schema constraints reject malformed states.

## Tests
- `test_domain_models_instantiation`
- `test_execution_state_defaults_and_transitions`

## Definition of Done
Domain models isolated from framework logic, 100% typed, test coverage complete.
