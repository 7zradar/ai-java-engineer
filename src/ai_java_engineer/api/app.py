"""FastAPI Application exposing REST API and Web Dashboard for AI Java Engineer platform."""

from pathlib import Path
from typing import Any
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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


def serialize_helper(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {k: serialize_helper(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_helper(i) for i in obj]
    return obj


class CreateRunRequest(BaseModel):
    title: str = Field(..., example="Customer Order History API")
    requirement_text: str = Field(..., example="Create GET /api/v1/customers/{id}/orders endpoint")
    workspace_path: str | None = Field(default=None, example="./sample_repo")
    require_human_pr_approval: bool = Field(default=True)
    constraints: list[str] | None = Field(default=None)


class ApproveRunRequest(BaseModel):
    reviewer: str = Field(..., example="lead-architect")
    decision: str = Field(default="APPROVE", example="APPROVE")
    feedback: str | None = None


@app.get("/", include_in_schema=False)
async def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "AI Java Engineer Platform API. Visit /docs for Swagger or /static/index.html for dashboard."
    }


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
    try:
        provider = get_configured_provider()
        backend = get_configured_backend()
        tracer = RUN_TRACERS.get(exec_id) or ExecutionTracer(exec_id)
        RUN_TRACERS[exec_id] = tracer

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
    except Exception as e:
        logger.error("Pipeline execution encountered an error", execution_id=exec_id, error=str(e))
        state["status"] = RunStatus.FAILED
        state["escalation_reason"] = f"Execution error: {str(e)}"
        RUN_STATES[exec_id] = state


@app.get("/runs")
async def list_runs():
    db_runs = checkpoint_store.list_all_runs(limit=30)
    active_runs = []
    seen = {r["execution_id"] for r in db_runs}
    for exec_id, state in RUN_STATES.items():
        if exec_id not in seen:
            req = state.get("requirement")
            title = ""
            if hasattr(req, "title"):
                title = req.title
            elif isinstance(req, dict):
                title = req.get("title", "")
            status_val = state.get("status")
            if hasattr(status_val, "value"):
                status_val = status_val.value

            active_runs.append({
                "execution_id": exec_id,
                "node_name": "active",
                "status": str(status_val),
                "created_at": "En progreso",
                "title": title or exec_id,
                "iteration": state.get("iteration", 0),
                "changed_files_count": len(state.get("changed_files", [])),
            })
    return active_runs + db_runs


@app.post("/runs")
async def create_run(req: CreateRunRequest, background_tasks: BackgroundTasks):
    exec_id = f"RUN-{uuid.uuid4().hex[:8]}"
    tracer = ExecutionTracer(exec_id)
    RUN_TRACERS[exec_id] = tracer

    ws_path = req.workspace_path
    if not ws_path or ws_path.strip().lower() in ("sandbox", "./sandbox_workspace", "default", ""):
        sandbox_base = Path("./workspaces").resolve()
        sandbox_base.mkdir(parents=True, exist_ok=True)
        ws_path = str(sandbox_base / exec_id)
        Path(ws_path).mkdir(parents=True, exist_ok=True)
    else:
        ws_path = str(Path(ws_path).resolve())
        Path(ws_path).mkdir(parents=True, exist_ok=True)

    constraints = req.constraints or ["Spring Boot 3.3", "Java 21", "Pure JUnit 5 unit tests"]

    requirement = RequirementSpec(
        id=exec_id,
        title=req.title,
        raw_text=req.requirement_text,
        target_repository=ws_path,
        constraints=constraints,
    )

    initial_state: EngineeringState = {
        "execution_id": exec_id,
        "workspace_path": ws_path,
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
        "status": RunStatus.PENDING.value,
        "trace_id": tracer.trace_id,
        "workspace_path": ws_path,
        "message": "Run triggered asynchronously.",
    }


@app.get("/runs/{execution_id}")
async def get_run(execution_id: str):
    state = RUN_STATES.get(execution_id)
    if not state:
        loaded = checkpoint_store.load_latest_checkpoint(execution_id)
        if not loaded:
            raise HTTPException(status_code=404, detail="Run not found")
        state = loaded

    ws_path = state.get("workspace_path", "")
    changed_files = state.get("changed_files", [])
    files_content: dict[str, str] = {}
    if ws_path and Path(ws_path).exists():
        ws_root = Path(ws_path).resolve()
        for cf in changed_files:
            try:
                target_file = (ws_root / cf.lstrip("/\\")).resolve()
                if target_file.exists() and target_file.is_file():
                    files_content[cf] = target_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

    timeline = checkpoint_store.get_checkpoints_timeline(execution_id)

    status_val = state.get("status")
    if hasattr(status_val, "value"):
        status_val = status_val.value

    return {
        "execution_id": state.get("execution_id"),
        "status": status_val,
        "iteration": state.get("iteration", 0),
        "workspace_path": str(ws_path),
        "changed_files": changed_files,
        "files_content": files_content,
        "requirement": serialize_helper(state.get("requirement")),
        "product_spec": serialize_helper(state.get("product_spec")),
        "architecture_spec": serialize_helper(state.get("architecture_spec")),
        "build_result": serialize_helper(state.get("build_result")),
        "test_result": serialize_helper(state.get("test_result")),
        "security_result": serialize_helper(state.get("security_result")),
        "review_result": serialize_helper(state.get("review_result")),
        "pr_payload": serialize_helper(state.get("pr_payload")),
        "escalation_reason": state.get("escalation_reason"),
        "human_approved": state.get("human_approved", False),
        "timeline": timeline,
    }


@app.post("/runs/{execution_id}/approve")
async def approve_run(
    execution_id: str,
    approval: ApproveRunRequest,
    background_tasks: BackgroundTasks,
):
    state = RUN_STATES.get(execution_id)
    if not state:
        loaded = checkpoint_store.load_latest_checkpoint(execution_id)
        if not loaded:
            raise HTTPException(status_code=404, detail="Run not found")
        state = loaded
        RUN_STATES[execution_id] = state

    status_val = state.get("status")
    status_str = status_val.value if hasattr(status_val, "value") else str(status_val)

    if status_str != RunStatus.WAITING_APPROVAL.value:
        raise HTTPException(status_code=400, detail=f"Run is not waiting approval (current: {status_str})")

    if approval.decision.upper() == "APPROVE":
        state["human_approved"] = True
        state["status"] = RunStatus.RUNNING
        background_tasks.add_task(_execute_pipeline, execution_id, state, False)
        return {"execution_id": execution_id, "status": "RESUMED", "message": "Approval granted, resuming PR creation."}
    else:
        state["status"] = RunStatus.FAILED
        state["escalation_reason"] = f"Rejected by reviewer {approval.reviewer}: {approval.feedback or 'No comment'}"
        checkpoint_store.save_checkpoint(
            execution_id=execution_id,
            node_name="human_rejected",
            status=RunStatus.FAILED,
            state=state,
        )
        return {"execution_id": execution_id, "status": "REJECTED"}


@app.get("/runs/{execution_id}/trace")
async def get_trace(execution_id: str):
    tracer = RUN_TRACERS.get(execution_id)
    if not tracer:
        raise HTTPException(status_code=404, detail="Trace not found for execution")
    return tracer.get_trace_report()
