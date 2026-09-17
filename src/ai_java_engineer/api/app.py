"""FastAPI Application exposing REST API for AI Java Engineer platform."""

import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_java_engineer.domain.execution import RunStatus
from ai_java_engineer.domain.requirement import RequirementSpec
from ai_java_engineer.execution.local_mock import LocalMockBackend
from ai_java_engineer.execution.remote_ci import RemoteCiExecutionBackend
from ai_java_engineer.infrastructure.logging import configure_logging, get_logger
from ai_java_engineer.infrastructure.settings import get_settings
from ai_java_engineer.llm.providers.gemini_provider import GeminiProvider
from ai_java_engineer.llm.providers.mock_provider import MockProvider
from ai_java_engineer.llm.providers.openai_provider import OpenAIProvider
from ai_java_engineer.observability.tracing import ExecutionTracer
from ai_java_engineer.orchestration.checkpoints import CheckpointStore
from ai_java_engineer.orchestration.graph import EngineeringOrchestrator
from ai_java_engineer.orchestration.state import EngineeringState

configure_logging()
logger = get_logger("api")

app = FastAPI(
    title="AI Java Engineer Platform API",
    version="0.1.0",
    description="Governed, observable, and reproducible multi-agent platform for Java feature engineering.",
)

# In-memory storage for active run states and tracers (backed by SQLite checkpoints)
RUN_STATES: dict[str, EngineeringState] = {}
RUN_TRACERS: dict[str, ExecutionTracer] = {}
checkpoint_store = CheckpointStore()


def get_configured_provider():
    settings = get_settings()
    if settings.default_llm_provider == "gemini" and settings.gemini_api_key:
        return GeminiProvider(settings.gemini_api_key)
    if settings.default_llm_provider == "openai" and settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key)
    return MockProvider()


def get_configured_backend():
    settings = get_settings()
    if settings.execution_backend == "remote_ci" and settings.remote_ci_endpoint:
        return RemoteCiExecutionBackend(
            endpoint_url=settings.remote_ci_endpoint,
            auth_token=settings.remote_ci_auth_token,
            timeout_seconds=settings.remote_ci_timeout_seconds,
        )
    return LocalMockBackend()


class CreateRunRequest(BaseModel):
    title: str = Field(..., example="Customer Order History API")
    requirement_text: str = Field(..., example="Create GET /api/v1/customers/{id}/orders endpoint")
    workspace_path: str = Field(..., example="./sample_repo")
    require_human_pr_approval: bool = Field(default=True)


class ApproveRunRequest(BaseModel):
    reviewer: str = Field(..., example="lead-architect")
    decision: str = Field(default="APPROVE", example="APPROVE")
    feedback: str | None = None


@app.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "HEALTHY",
        "env": settings.env,
        "llm_provider": settings.default_llm_provider,
        "execution_backend": settings.execution_backend,
        "version": "0.1.0",
    }


async def _execute_pipeline(exec_id: str, state: EngineeringState, require_human_approval: bool):
    provider = get_configured_provider()
    backend = get_configured_backend()
    tracer = RUN_TRACERS[exec_id]

    orchestrator = EngineeringOrchestrator(
        provider=provider,
        backend=backend,
        checkpoint_store=checkpoint_store,
        require_human_pr_approval=require_human_approval,
    )

    span = tracer.start_span("full_pipeline")
    final_state = await orchestrator.run(state)
    tracer.end_span(span, status=final_state["status"].value)
    RUN_STATES[exec_id] = final_state


@app.post("/runs")
async def create_run(req: CreateRunRequest, background_tasks: BackgroundTasks):
    exec_id = f"RUN-{uuid.uuid4().hex[:8]}"
    tracer = ExecutionTracer(exec_id)
    RUN_TRACERS[exec_id] = tracer

    requirement = RequirementSpec(
        id=exec_id,
        title=req.title,
        raw_text=req.requirement_text,
        target_repository=req.workspace_path,
    )

    initial_state: EngineeringState = {
        "execution_id": exec_id,
        "workspace_path": req.workspace_path,
        "requirement": requirement,
        "status": RunStatus.PENDING,
        "human_approved": False,
    }

    RUN_STATES[exec_id] = initial_state
    background_tasks.add_task(
        _execute_pipeline, exec_id, initial_state, req.require_human_pr_approval
    )

    return {
        "execution_id": exec_id,
        "status": RunStatus.PENDING,
        "trace_id": tracer.trace_id,
        "message": "Run triggered asynchronously.",
    }


@app.get("/runs/{execution_id}")
async def get_run(execution_id: str):
    state = RUN_STATES.get(execution_id)
    if not state:
        # Check SQLite
        loaded = checkpoint_store.load_latest_checkpoint(execution_id)
        if not loaded:
            raise HTTPException(status_code=404, detail="Run not found")
        return loaded

    # Return clean serializable summary
    return {
        "execution_id": state.get("execution_id"),
        "status": state.get("status"),
        "iteration": state.get("iteration"),
        "changed_files": state.get("changed_files", []),
        "build_passed": state["build_result"].success if state.get("build_result") else None,
        "test_passed": state["test_result"].passed if state.get("test_result") else None,
        "security_passed": state["security_result"].passed if state.get("security_result") else None,
        "review_verdict": state["review_result"].verdict if state.get("review_result") else None,
        "pr_payload": state.get("pr_payload"),
        "escalation_reason": state.get("escalation_reason"),
    }


@app.post("/runs/{execution_id}/approve")
async def approve_run(
    execution_id: str,
    approval: ApproveRunRequest,
    background_tasks: BackgroundTasks,
):
    state = RUN_STATES.get(execution_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")

    if state.get("status") != RunStatus.WAITING_APPROVAL:
        raise HTTPException(status_code=400, detail=f"Run is not waiting approval (current: {state.get('status')})")

    if approval.decision == "APPROVE":
        state["human_approved"] = True
        state["status"] = RunStatus.RUNNING
        background_tasks.add_task(_execute_pipeline, execution_id, state, False)
        return {"execution_id": execution_id, "status": "RESUMED", "message": "Approval granted, resuming PR creation."}
    else:
        state["status"] = RunStatus.FAILED
        state["escalation_reason"] = f"Rejected by reviewer {approval.reviewer}: {approval.feedback}"
        return {"execution_id": execution_id, "status": "REJECTED"}


@app.get("/runs/{execution_id}/trace")
async def get_trace(execution_id: str):
    tracer = RUN_TRACERS.get(execution_id)
    if not tracer:
        raise HTTPException(status_code=404, detail="Trace not found for execution")
    return tracer.get_trace_report()
