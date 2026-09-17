# SPEC-004: Tool Contract Layer

## Objective
Provide deterministic, isolated filesystem, repository inspection, and patching tools with strict path containment boundaries and audit logging.

## Context
Agents must never be allowed arbitrary disk access (e.g. `../../etc/passwd` or system files). All filesystem interactions must be bounded to the target project workspace root.

## Scope
- Tool schemas: `ReadFileInput`, `ReadFileOutput`, `WriteFileInput`, `WriteFileOutput`, `ApplyPatchInput`, `ApplyPatchOutput`.
- Workspace boundary validation (`pathlib.Path.resolve()` containment).
- SHA-256 fingerprinting for idempotent operations.
- Security event logging upon containment breach.

## Non-scope
- Arbitrary bash/shell execution by LLM agents.

## Functional Requirements
- FR-4.1: `read_file` shall read files within workspace with optional line slice bounds.
- FR-4.2: `write_file` shall write content atomically, ensuring parent directories exist.
- FR-4.3: `apply_patch` shall parse unified diffs or targeted search/replace blocks with idempotency.
- FR-4.4: Any path resolving outside workspace root shall raise `SecurityViolationError`.

## Architecture & Schemas
```python
class ReadFileInput(BaseModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None

class ReadFileOutput(BaseModel):
    path: str
    content: str
    sha256: str
    truncated: bool
```

## Security Considerations
All path inputs undergo canonicalization and boundary verification before any OS calls.

## Observability
Emit structured audit events for every file read, written, or patched.

## Failure Handling
Raise `FileNotFoundError`, `PathOutOfBoundsError`, or `PatchApplicationError` with clear diagnostics.

## Acceptance Criteria
- Attempts to access paths outside workspace root fail with security exceptions.
- Line slicing works accurately on Windows CRLF and UNIX LF.

## Tests
- `test_filesystem_boundary_containment`
- `test_atomic_write_and_sha256_verification`
- `test_apply_patch_idempotency`

## Definition of Done
Tools strictly enforce boundaries, 100% test coverage on security invariants.
