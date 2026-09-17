# SPEC-009: Coding Agent

## Objective
Generate production-ready, idiomatic Java 21 / Spring Boot code and corresponding JUnit 5 test suites strictly compliant with the `ArchitectureSpec` and repository standards.

## Context
The Coding Agent must not output chatty conversational answers. It outputs deterministic file creation operations and surgical patches targeting precise file paths within the workspace.

## Scope
- Input: `ProductSpec`, `ArchitectureSpec`, `RepositoryContext`.
- Output: `CodePlan` (list of new files and patch modifications).
- Language: Modern Java 21 (records, pattern matching, Jakarta EE, Spring Boot 3+).
- Unit Tests: JUnit 5, AssertJ, Mockito.

## Non-scope
- Arbitrary script generation or direct terminal execution.

## Functional Requirements
- FR-9.1: Generate standard Spring Boot layered architecture classes (Controller, Service, Repository, DTO).
- FR-9.2: Generate corresponding unit test classes covering happy path, null handling, and edge cases.
- FR-9.3: Ensure all imports (`jakarta.*`, `org.springframework.*`) are explicit and non-wildcard.

## Schemas
```python
class FileAction(BaseModel):
    path: str
    action: Literal["CREATE", "MODIFY", "DELETE"]
    content: str
    description: str

class CodePlan(BaseModel):
    summary: str
    actions: list[FileAction]
```

## Security Considerations
Generated code must adhere to secure coding standards (e.g. parameterized queries, avoid raw SQL, validate DTOs with `@Valid` / `@NotNull`).

## Observability
Record number of files generated, lines of code, and token utilization.

## Failure Handling
Schema validation rejects malformed file paths or missing contents.

## Acceptance Criteria
- Emits structured `CodePlan` with valid Java syntax and corresponding unit tests.

## Tests
- `test_coding_agent_generates_spring_boot_components`
- `test_coding_agent_generates_junit5_tests`

## Definition of Done
Coding Agent outputs structured `CodePlan` adhering to Spring Boot conventions.
