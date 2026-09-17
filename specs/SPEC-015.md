# SPEC-015: Human Approval Gate

## Objective
Implement deterministic Human-in-the-Loop (HITL) checkpoints in the state machine at critical decision boundaries: architecture approval, security policy escalations, test failure budget exhaustion, and final Pull Request creation.

## Context
Full autonomy without governance is dangerous in enterprise environments. Humans should not be burdened with trivial micro-decisions, but must hold authority over irreversible actions and critical escalations.

## Scope
- LangGraph pause/interrupt primitives and state resumption.
- API endpoints: `GET /runs/{id}/approval-status` and `POST /runs/{id}/approve`.
- Approval decision logging with human reviewer ID, decision (`APPROVE`, `REJECT`), and feedback.

## Non-scope
- Real-time video/chat conferencing interfaces.

## Functional Requirements
- FR-15.1: State machine transitions to `WAITING_APPROVAL` before mutating remote git repositories.
- FR-15.2: An external call to `POST /runs/{id}/approve` resumes execution from the exact checkpoint.
- FR-15.3: An external rejection aborts the pipeline or redirects to replanning based on human feedback.

## Schemas
```python
class ApprovalGateType(str, Enum):
    ARCHITECTURE_REVIEW = "ARCHITECTURE_REVIEW"
    CRITICAL_SECURITY = "CRITICAL_SECURITY"
    MAX_ITERATIONS_EXCEEDED = "MAX_ITERATIONS_EXCEEDED"
    PULL_REQUEST_CREATION = "PULL_REQUEST_CREATION"

class ApprovalDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT", "MODIFY"]
    reviewer: str
    feedback: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

## Security Considerations
Only authorized human users or tokens may trigger approval endpoints.

## Observability
Logs time spent waiting in human approval queues to accurately distinguish AI runtime from human latency.

## Failure Handling
Timeout policies automatically escalate or transition stale runs to `EXPIRED`.

## Acceptance Criteria
- Execution halts cleanly at designated approval nodes and resumes immediately upon receiving approval payload.

## Tests
- `test_human_approval_gate_pauses_execution`
- `test_human_approval_resumption_continues_graph`

## Definition of Done
HITL gates integrated cleanly with LangGraph checkpointing and REST API.
