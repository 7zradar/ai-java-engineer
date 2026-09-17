# SPEC-006: Product Agent

## Objective
Convert raw natural language feature requests or user tickets into formal, unambiguous `ProductSpec` objects containing user stories, acceptance criteria, business rules, edge cases, and explicit non-goals.

## Context
Engineering failures frequently stem from ambiguous requirements. The Product Agent acts as the front door, ensuring that downstream architectural and coding agents receive structured, testable specifications.

## Scope
- Prompt template: `prompts/product/v1.md`.
- Input: `RequirementSpec` (title, raw description, constraints).
- Output: `ProductSpec` with typed fields.
- Validation of acceptance criteria testability.

## Non-scope
- Multi-stakeholder negotiation or UI wireframing.

## Functional Requirements
- FR-6.1: Extract at least one primary user story following the "As a... I want... So that..." pattern.
- FR-6.2: Generate discrete, falsifiable acceptance criteria (Given-When-Then format).
- FR-6.3: Identify edge cases, null inputs, and error states.

## Schemas
```python
class AcceptanceCriterion(BaseModel):
    id: str
    scenario: str
    given: str
    when: str
    then: str

class ProductSpec(BaseModel):
    title: str
    user_stories: list[UserStory]
    acceptance_criteria: list[AcceptanceCriterion]
    business_rules: list[str]
    edge_cases: list[str]
    assumptions: list[str]
```

## Security Considerations
Sanitize untrusted input strings to eliminate hidden prompt injection attempts.

## Observability
Record prompt version, tokens consumed, and generation latency.

## Failure Handling
If the LLM output fails schema validation, invoke structured-repair retry up to 2 times.

## Acceptance Criteria
- Given a raw feature requirement, produce a fully validated `ProductSpec` object.

## Tests
- `test_product_agent_generates_valid_spec`
- `test_product_agent_schema_repair_on_invalid_json`

## Definition of Done
Product Agent functional, outputs validated against `ProductSpec` schema, tests pass.
