# SPEC-012: Autonomous Debug Loop

## Objective
Implement an autonomous self-healing debug loop that analyzes Maven compilation errors or JUnit assertion failures, computes failure fingerprints to detect cycles, and produces surgical patches up to a hard iteration ceiling.

## Context
Naively looping `try_again()` causes agents to hallucinate repetitive or circular patches. The debug loop must fingerprint the error, analyze the precise root cause, and verify whether the patch resolved the specific failure.

## Scope
- Input: `BuildResult` or `TestResult`, failing source files, diff history.
- `FailureFingerprint`: SHA-256 hash of normalized error message and failing file/line to detect infinite loops.
- Debug Agent prompts (`prompts/debugger/v1.md`).
- Hard iteration guardrail (maximum 3 debug cycles).

## Non-scope
- Rewriting the entire architectural specification during debugging.

## Functional Requirements
- FR-12.1: Extract the first 3 primary compiler errors or test failure stacktraces.
- FR-12.2: Compute a deterministic `FailureFingerprint`.
- FR-12.3: If identical fingerprint appears consecutively, escalate to human or abort to prevent token burning.
- FR-12.4: Generate targeted patches correcting syntax, imports, or assertion mismatches.

## Schemas
```python
class FailureFingerprint(BaseModel):
    fingerprint_hash: str
    error_type: str # e.g. COMPILATION_ERROR, ASSERTION_FAILURE
    file: str | None
    line: int | None
    message_summary: str

class DebugAction(BaseModel):
    analysis: str
    root_cause: str
    patches: list[FileAction]
```

## Security Considerations
Debug agent patches are subject to the same filesystem boundary and security scanning checks as the initial coding phase.

## Observability
Tracks iteration count, error fingerprint history, and resolution time.

## Failure Handling
Upon exceeding `max_debug_iterations`, transitions run state to `HUMAN_ESCALATION` without crashing.

## Acceptance Criteria
- Successfully repairs simulated Java compilation errors within 1-2 iterations.
- Detects repeated fingerprints and halts cleanly.

## Tests
- `test_failure_fingerprinting_computation`
- `test_debug_loop_max_iteration_ceiling`
- `test_debug_agent_patch_generation`

## Definition of Done
Debug loop autonomously fixes targeted errors and respects hard iteration boundaries.
