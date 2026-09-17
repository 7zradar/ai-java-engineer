# SPEC-017: Observability

## Objective
Provide deep, production-grade observability across all agent reasoning steps and deterministic tool executions, recording OpenTelemetry-compatible traces, node latencies, token consumption, and cost calculations.

## Context
A senior engineering platform must be fully observable. When an agent fails or takes 3 minutes to execute, operators must be able to inspect a clear trace breakdown showing exact latencies, token counts, and tool responses.

## Scope
- `ExecutionTracer`: records spans for each agent node (`product`, `architect`, `coder`, `build`, `test`, `debug`, `security`, `review`).
- Token accounting: prompt tokens, completion tokens, cached tokens, and estimated USD cost.
- Export formats: in-memory span trees, JSON audit traces, and OpenTelemetry OTLP compatible data.

## Non-scope
- Running heavy distributed tracing collectors (Jaeger/Prometheus) locally.

## Functional Requirements
- FR-17.1: Every run generates a globally unique `trace_id`.
- FR-17.2: Every node execution creates a child span with start time, end time, duration, and status.
- FR-17.3: Calculate total cost using a configurable model pricing matrix.

## Schemas
```python
class SpanRecord(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: int = 0
    attributes: dict[str, Any] = Field(default_factory=dict)
    status: Literal["OK", "ERROR"] = "OK"

class RunTrace(BaseModel):
    trace_id: str
    execution_id: str
    total_duration_ms: int
    total_tokens: int
    estimated_cost_usd: float
    spans: list[SpanRecord]
```

## Security Considerations
Traces must pass through the `SecretSanitizer` before persisting to disk or returning via API.

## Observability
Tracer monitors its own overhead, ensuring tracing introduces less than 5ms overhead per node.

## Failure Handling
Tracing failures must be non-blocking; the primary execution pipeline must continue even if telemetry export encounters an error.

## Acceptance Criteria
- Run generates a complete trace report breaking down execution time and cost per node.

## Tests
- `test_execution_tracer_span_hierarchy`
- `test_cost_calculation_pricing_matrix`

## Definition of Done
Observability layer records and exposes traces for every execution.
