"""Integration tests for state machine transitions and checkpointing."""

import tempfile

import pytest

from ai_java_engineer.domain.execution import RunStatus
from ai_java_engineer.domain.requirement import RequirementSpec
from ai_java_engineer.execution.local_mock import LocalMockBackend
from ai_java_engineer.llm.providers.mock_provider import MockProvider
from ai_java_engineer.orchestration.checkpoints import CheckpointStore
from ai_java_engineer.orchestration.graph import EngineeringOrchestrator
from ai_java_engineer.orchestration.state import EngineeringState


@pytest.mark.asyncio
async def test_state_machine_happy_path():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        db_path = f"{temp_dir}/test_checkpoints.db"
        checkpoint_store = CheckpointStore(db_path=db_path)
        provider = MockProvider()
        backend = LocalMockBackend()

        orchestrator = EngineeringOrchestrator(
            provider=provider,
            backend=backend,
            checkpoint_store=checkpoint_store,
            require_human_pr_approval=False,
        )

        req = RequirementSpec(
            id="RUN-TEST-01",
            title="Create Order Endpoint",
            raw_text="Expose GET /api/v1/customers/{id}/orders",
            target_repository=temp_dir,
        )

        initial_state: EngineeringState = {
            "execution_id": "RUN-TEST-01",
            "workspace_path": temp_dir,
            "requirement": req,
        }

        final_state = await orchestrator.run(initial_state)

        assert final_state["status"] == RunStatus.COMPLETED
        assert final_state["product_spec"] is not None
        assert final_state["architecture_spec"] is not None
        assert final_state["build_result"].success is True
        assert final_state["test_result"].passed is True
        assert final_state["security_result"].passed is True
        assert final_state["review_result"].verdict == "APPROVED"
        assert final_state["pr_payload"] is not None

        # Verify SQLite checkpoint was persisted
        latest_cp = checkpoint_store.load_latest_checkpoint("RUN-TEST-01")
        assert latest_cp is not None
        assert latest_cp["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_state_machine_human_approval_gate():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        db_path = f"{temp_dir}/test_checkpoints.db"
        checkpoint_store = CheckpointStore(db_path=db_path)
        provider = MockProvider()
        backend = LocalMockBackend()

        orchestrator = EngineeringOrchestrator(
            provider=provider,
            backend=backend,
            checkpoint_store=checkpoint_store,
            require_human_pr_approval=True,
        )

        req = RequirementSpec(
            id="RUN-TEST-02",
            title="Create Order Endpoint with Approval",
            raw_text="Expose GET /api/v1/customers/{id}/orders",
            target_repository=temp_dir,
        )

        initial_state: EngineeringState = {
            "execution_id": "RUN-TEST-02",
            "workspace_path": temp_dir,
            "requirement": req,
        }

        state_paused = await orchestrator.run(initial_state)
        # Should stop at WAITING_APPROVAL before creating PR
        assert state_paused["status"] == RunStatus.WAITING_APPROVAL
        assert state_paused.get("pr_payload") is None

        # Simulate Human approving
        state_paused["human_approved"] = True
        state_resumed = await orchestrator.run(state_paused)
        assert state_resumed["status"] == RunStatus.COMPLETED
        assert state_resumed.get("pr_payload") is not None
