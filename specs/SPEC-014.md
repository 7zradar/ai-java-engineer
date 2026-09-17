# SPEC-014: Review Agent

## Objective
Perform contract-driven code review evaluating the generated git diff against the original `ProductSpec`, `ArchitectureSpec`, and test evidence, producing structured review verdicts.

## Context
Code review must not be a superficial LLM opinion like "looks good to me". It must cross-reference actual file changes, verify whether all acceptance criteria have corresponding tests, and check adherence to architectural decisions.

## Scope
- Input: `ProductSpec`, `ArchitectureSpec`, Git diff, `TestResult`, `SecurityResult`.
- Output: `ReviewResult` with discrete checklist item statuses.
- Prompt template: `prompts/reviewer/v1.md`.

## Non-scope
- Automated merging or PR approval without human consent.

## Functional Requirements
- FR-14.1: Verify each acceptance criterion has passing test coverage in `TestResult`.
- FR-14.2: Verify package and entity naming conforms to `ArchitectureSpec`.
- FR-14.3: Issue a structured verdict: `APPROVED`, `CHANGES_REQUESTED`, or `REJECTED`.

## Schemas
```python
class ReviewChecklistItem(BaseModel):
    name: str
    passed: bool
    details: str

class ReviewResult(BaseModel):
    verdict: Literal["APPROVED", "CHANGES_REQUESTED", "REJECTED"]
    score: float # 0.0 - 1.0
    summary: str
    checklist: list[ReviewChecklistItem]
    required_changes: list[str]
```

## Security Considerations
Review agent verifies that no unapproved third-party dependencies or licenses were introduced.

## Observability
Record review score, review time, and number of requested changes.

## Failure Handling
Verdict `CHANGES_REQUESTED` routes back to coder or debugger if within iteration limits.

## Acceptance Criteria
- Produces rigorous, contract-based review results with itemized checklist scores.

## Tests
- `test_review_agent_approves_compliant_diff`
- `test_review_agent_requests_changes_on_untested_criterion`

## Definition of Done
Review Agent operational and integrated into state machine prior to PR creation.
