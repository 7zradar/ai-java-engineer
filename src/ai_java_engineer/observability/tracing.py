"""OpenTelemetry-compatible Tracing and Cost Accounting."""

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from ai_java_engineer.security.sanitizer import SecretSanitizer


class SpanRecord(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: int = 0
    attributes: dict[str, Any] = Field(default_factory=dict)
    status: str = "OK"


class RunTrace(BaseModel):
    trace_id: str
    execution_id: str
    total_duration_ms: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    spans: list[SpanRecord] = Field(default_factory=list)


class ExecutionTracer:
    """Tracks latency, spans, token consumption, and dollar costs per execution."""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.trace_id = f"AIJ-{uuid.uuid4().hex[:8]}"
        self.spans: list[SpanRecord] = []
        self.start_time = time.time()
        self.total_tokens = 0
        self.estimated_cost_usd = 0.0

    def start_span(self, name: str, parent_span_id: str | None = None) -> SpanRecord:
        span = SpanRecord(
            span_id=uuid.uuid4().hex[:12],
            parent_span_id=parent_span_id,
            name=name,
            start_time=time.time(),
        )
        self.spans.append(span)
        return span

    def end_span(
        self,
        span: SpanRecord,
        status: str = "OK",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        span.end_time = time.time()
        span.duration_ms = int((span.end_time - span.start_time) * 1000)
        span.status = status
        if attributes:
            clean_attrs = SecretSanitizer.sanitize_dict(attributes)
            span.attributes.update(clean_attrs)

    def record_cost(self, tokens: int, cost_usd: float) -> None:
        self.total_tokens += tokens
        self.estimated_cost_usd += cost_usd

    def get_trace_report(self) -> RunTrace:
        total_duration = int((time.time() - self.start_time) * 1000)
        return RunTrace(
            trace_id=self.trace_id,
            execution_id=self.execution_id,
            total_duration_ms=total_duration,
            total_tokens=self.total_tokens,
            estimated_cost_usd=round(self.estimated_cost_usd, 4),
            spans=self.spans,
        )
