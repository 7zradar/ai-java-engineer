# SPEC-007: Architect Agent

## Objective
Transform a `ProductSpec` and repository context into a concrete `ArchitectureSpec` tailored for Spring Boot / Java 21, including package layouts, REST contracts, JPA entities, Maven dependencies, and Architecture Decision Records (ADRs).

## Context
Writing code without prior architectural synthesis leads to broken package hierarchies, conflicting dependencies, and duplicate abstractions. The Architect Agent establishes the technical blueprint.

## Scope
- Input: `ProductSpec`, `RepositoryMap`.
- Output: `ArchitectureSpec` (components, endpoints, entities, Maven dependencies, ADRs).
- Prompt template: `prompts/architect/v1.md`.

## Non-scope
- Database migration scripting or infrastructure-as-code generation.

## Functional Requirements
- FR-7.1: Identify target packages conforming to existing project conventions (e.g. `controller`, `service`, `repository`, `domain`).
- FR-7.2: Specify REST endpoints (HTTP method, path, request/response DTOs, status codes).
- FR-7.3: Check if new Maven dependencies are strictly necessary and conform to approved libraries.

## Schemas
```python
class EndpointSpec(BaseModel):
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    path: str
    description: str
    request_dto: str | None = None
    response_dto: str
    status_code: int = 200

class ArchitectureSpec(BaseModel):
    summary: str
    packages_to_modify: list[str]
    endpoints: list[EndpointSpec]
    entities: list[str]
    dependencies_needed: list[str]
    architecture_decisions: list[str]
```

## Security Considerations
Enforce Spring Security conventions (e.g. authentication requirements for protected endpoints).

## Observability
Record architecture complexity metrics (number of components, new dependencies).

## Failure Handling
Return structured errors if the requirement contradicts existing repository architecture.

## Acceptance Criteria
- Architecture spec contains verified Spring Boot component designs.

## Tests
- `test_architect_agent_produces_valid_architecture_spec`
- `test_architect_agent_detects_existing_packages`

## Definition of Done
Architect Agent integrated with repository context, passing schema validation.
