# SPEC-001: Engineering Foundation

## Objective
Establish the core engineering standards, directory architecture, runtime dependencies, logging, error hierarchy, configuration management, and developer toolchain for the `ai-java-engineer` platform.

## Context
A research-grade AI agent platform must avoid improvised scripts. It requires strict typing, automated linting, structured logging, and declarative configuration. The host environment only has Python available, requiring a lightweight, reproducible ecosystem.

## Scope
- Directory layout conforming to clean/hexagonal architecture.
- Pydantic Settings integration for environment variables.
- Structured JSON logging via `structlog`.
- Central error hierarchy with error codes.
- Development tooling: Ruff, Mypy, Pytest.
- Healthcheck endpoint `/health`.

## Non-scope
- Multi-tenant cloud deployments.
- Heavy containerization or Kubernetes manifests.

## Functional Requirements
- FR-1.1: The system shall load settings from environment variables and `.env` with validation.
- FR-1.2: The system shall emit structured logs in JSON format in production and console-colored in development.
- FR-1.3: The system shall provide an application error hierarchy rooted at `PlatformError` with HTTP status mapping.

## Non-functional Requirements
- Startup latency under 500ms.
- 100% type annotations with strict mypy passing.

## Architecture & Interfaces
- Module: `ai_java_engineer.infrastructure.settings` (`AppSettings`)
- Module: `ai_java_engineer.infrastructure.logging` (`configure_logging`)
- Module: `ai_java_engineer.domain.errors` (`PlatformError`, `ConfigurationError`, `SecurityViolationError`)

## Schemas
```python
class AppSettings(BaseSettings):
    env: str = "development"
    log_level: str = "INFO"
    default_llm_provider: str = "mock"
    database_url: str = "sqlite+aiosqlite:///./ai_java_engineer.db"
    max_total_tokens: int = 250000
    max_debug_iterations: int = 3
```

## Security Considerations
Settings must avoid dumping sensitive API keys in `__repr__` or raw logs.

## Observability
Logs will include `execution_id`, `step_id`, and `timestamp` fields.

## Failure Handling
Missing mandatory variables crash fast at startup with descriptive diagnostics.

## Acceptance Criteria
- `AppSettings` loads defaults and overrides cleanly.
- `GET /health` returns HTTP 200 with uptime and environment status.

## Tests
- `test_settings_loading_and_validation`
- `test_healthcheck_endpoint`

## Definition of Done
Code formatted with Ruff, passes Mypy, and unit tests pass with 100% assertion success.
