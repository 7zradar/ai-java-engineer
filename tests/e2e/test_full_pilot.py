"""End-to-End Pilot test validating the entire engineering pipeline and debug loop."""

import tempfile

import pytest

from ai_java_engineer.domain.execution import RunStatus
from ai_java_engineer.domain.requirement import RequirementSpec
from ai_java_engineer.evaluation.benchmark_runner import BenchmarkRunner
from ai_java_engineer.evaluation.metrics import BenchmarkTask
from ai_java_engineer.execution.local_mock import LocalMockBackend
from ai_java_engineer.llm.providers.mock_provider import MockProvider
from ai_java_engineer.orchestration.graph import EngineeringOrchestrator
from ai_java_engineer.orchestration.state import EngineeringState


@pytest.mark.asyncio
async def test_e2e_pilot_with_debug_loop():
    """Validates that a build failure triggers the autonomous debug loop and recovers."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        provider = MockProvider()
        # Backend configured to fail the first build attempt
        backend = LocalMockBackend(fail_first_build=True)

        orchestrator = EngineeringOrchestrator(
            provider=provider,
            backend=backend,
            require_human_pr_approval=False,
        )

        req = RequirementSpec(
            id="PILOT-001",
            title="Customer Order Feature with Self-Healing",
            raw_text="Build full order endpoint with pagination and error recovery",
            target_repository=temp_dir,
        )

        initial_state: EngineeringState = {
            "execution_id": "PILOT-001",
            "workspace_path": temp_dir,
            "requirement": req,
        }

        final_state = await orchestrator.run(initial_state)

        # Verified that debug loop ran at least 1 iteration and succeeded
        assert final_state["iteration"] == 1
        assert final_state["status"] == RunStatus.COMPLETED
        assert final_state["build_result"].success is True
        assert final_state["test_result"].passed is True
        assert final_state["pr_payload"] is not None


@pytest.mark.asyncio
async def test_e2e_benchmark_runner():
    """Runs a batch of evaluation tasks through the benchmark runner."""
    provider = MockProvider()
    runner = BenchmarkRunner(provider=provider)

    sample_tasks = [
        BenchmarkTask(
            task_id="EVAL-1",
            title="Sample CRUD",
            requirement="Create OrderController and tests",
            expected_classes=["OrderController.java", "OrderControllerTest.java"],
        ),
        BenchmarkTask(
            task_id="EVAL-2",
            title="Sample Validation",
            requirement="Add validator to Customer DTO",
            expected_classes=["OrderController.java"],
        ),
    ]

    report = await runner.run_benchmark(sample_tasks)
    assert report.total_tasks == 2
    assert report.build_success_rate == 1.0
    assert report.visible_test_pass_rate == 1.0
    assert report.hidden_test_pass_rate == 1.0
    assert report.average_cost_usd > 0
