# SPEC-010: Remote Build Adapter

## Objective
Decouple compilation and build execution from the local Python host machine by providing a pluggable `ExecutionBackend` protocol supporting local mocking and remote CI runner delegation (Java 21 + Maven).

## Context
The user's local laboratory machine has Python 3.12+ but lacks Java, Maven, Docker, and Node. Designing the platform to run Maven locally would violate physical constraints. The solution is an adapter executing `mvn compile` and `mvn test` in a remote sandbox or CI runner.

## Scope
- `ExecutionBackend` Protocol.
- `MockExecutionBackend`: Deterministic offline simulator capable of simulating compilation errors, test failures, and success passes for testing.
- `RemoteCiExecutionBackend`: Asynchronous HTTP/Webhook/GitHub Actions client dispatching builds to an external Java 21 + Maven environment.
- Execution payload bundling and log retrieval.

## Non-scope
- Provisioning cloud infrastructure or bare-metal hypervisors.

## Functional Requirements
- FR-10.1: Dispatches build requests with repository reference, branch, and timeout limits.
- FR-10.2: Polls or waits for execution completion and captures stdout, stderr, and exit code.
- FR-10.3: Returns structured `BuildResult` indicating compilation status and diagnostics.

## Interfaces & Schemas
```python
class BuildResult(BaseModel):
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    error_summary: str | None = None

class ExecutionBackend(Protocol):
    async def run_build(self, workspace_path: str, timeout_seconds: int = 300) -> BuildResult:
        ...

    async def run_tests(self, workspace_path: str, timeout_seconds: int = 300) -> TestResult:
        ...
```

## Security Considerations
Communication with remote CI runners must use TLS (HTTPS) and authenticate with bearer tokens stored securely.

## Observability
Logs network latencies, remote runner job IDs, and build durations.

## Failure Handling
Remote runner timeouts or network disconnects trigger configurable retries with circuit-breaker behavior.

## Acceptance Criteria
- `MockExecutionBackend` provides instant, controllable test harness for CI.
- `RemoteCiExecutionBackend` correctly packages requests and processes remote responses.

## Tests
- `test_mock_execution_backend_success_and_failure`
- `test_remote_ci_execution_backend_protocol`

## Definition of Done
Build execution cleanly abstracted from local Python machine; passes all interface tests.
