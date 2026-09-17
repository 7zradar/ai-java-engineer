# SPEC-020: End-to-End Pilot

## Objective
Demonstrate the complete, production-grade functioning of the `ai-java-engineer` platform from raw requirement ingestion to automated PR generation, self-healing debugging, and quantitative evaluation on a sample Spring Boot codebase.

## Context
The end-to-end pilot serves as the definitive proof-of-concept for presentation to the AI Research Lab, proving that probabilistic reasoning coupled with deterministic execution produces verified software artifacts.

## Scope
- Sample Spring Boot repository structure (`CustomerService`, `OrderService`, etc.).
- Complete pipeline execution covering all 9 agent nodes and execution adapters.
- Demonstration of autonomous compilation error recovery (Debug Loop).
- Demonstration of Human Approval gate before Git PR delivery.
- Verification of test execution and Surefire parsing.

## Non-scope
- Deploying live containers to external cloud providers.

## Functional Requirements
- FR-20.1: Given a feature requirement (e.g. "Add a GET /api/v1/customers/{id}/orders endpoint with status filtering and pagination"), execute the full pipeline.
- FR-20.2: Produce the architectural design, source files, and unit tests.
- FR-20.3: Successfully trigger the mock/remote execution backend and parse results.
- FR-20.4: If an intentional syntax error or assertion failure is introduced, recover within 1-2 debug iterations.
- FR-20.5: Generate the final Pull Request payload and execution trace report.

## Acceptance Criteria
- End-to-end integration test passes with 100% assertion coverage.
- Generates verified artifacts: `ProductSpec`, `ArchitectureSpec`, Java files, Surefire `TestResult`, `SecurityResult`, `ReviewResult`, and `PullRequestPayload`.

## Tests
- `test_e2e_pilot_execution_happy_path`
- `test_e2e_pilot_with_debug_loop_recovery`

## Definition of Done
Complete pipeline runs successfully from start to finish, outputting all verified deliverables and traces.
