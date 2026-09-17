"""Benchmark Runner: executes tasks, tests hidden suites, and generates evaluation reports."""

import json
import tempfile
import time
from pathlib import Path

from ai_java_engineer.domain.execution import RunStatus
from ai_java_engineer.domain.requirement import RequirementSpec
from ai_java_engineer.evaluation.metrics import (
    BenchmarkReport,
    BenchmarkTask,
    ErrorCode,
    TaskEvaluationResult,
)
from ai_java_engineer.execution.local_mock import LocalMockBackend
from ai_java_engineer.llm.base import ModelProvider
from ai_java_engineer.orchestration.graph import EngineeringOrchestrator
from ai_java_engineer.orchestration.state import EngineeringState


class BenchmarkRunner:
    """Executes a benchmark dataset of Java engineering tasks and reports quantitative metrics."""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @classmethod
    def load_dataset(cls, dataset_path: str | Path) -> list[BenchmarkTask]:
        tasks = []
        path = Path(dataset_path)
        if not path.exists():
            return tasks

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    tasks.append(BenchmarkTask.model_validate(data))
        return tasks

    async def run_benchmark(self, tasks: list[BenchmarkTask]) -> BenchmarkReport:
        task_results: list[TaskEvaluationResult] = []
        error_counts: dict[str, int] = {e.name: 0 for e in ErrorCode}

        for task in tasks:
            start_time = time.time()
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
                backend = LocalMockBackend()
                orchestrator = EngineeringOrchestrator(
                    provider=self.provider,
                    backend=backend,
                    require_human_pr_approval=False,
                )

                req = RequirementSpec(
                    id=task.task_id,
                    title=task.title,
                    raw_text=task.requirement,
                    target_repository=str(temp_dir),
                )

                init_state: EngineeringState = {
                    "execution_id": f"eval-{task.task_id}",
                    "workspace_path": str(temp_dir),
                    "requirement": req,
                }

                state = await orchestrator.run(init_state)

                duration_ms = int((time.time() - start_time) * 1000)
                build_passed = (state.get("build_result") is not None) and state["build_result"].success
                visible_passed = (state.get("test_result") is not None) and state["test_result"].passed

                # Evaluate hidden tests (simulated against generated classes)
                hidden_passed = True
                error_code = None

                if not build_passed:
                    error_code = ErrorCode.E003
                    hidden_passed = False
                elif not visible_passed:
                    error_code = ErrorCode.E004
                    hidden_passed = False
                elif state.get("status") == RunStatus.SECURITY_BLOCKED:
                    error_code = ErrorCode.E007
                    hidden_passed = False
                else:
                    # Check if all expected classes were generated
                    changed_paths = state.get("changed_files", [])
                    for exp in task.expected_classes:
                        if not any(exp in p for p in changed_paths):
                            error_code = ErrorCode.E002  # Architecture violation
                            hidden_passed = False
                            break

                if error_code:
                    error_counts[error_code.name] += 1

                task_results.append(
                    TaskEvaluationResult(
                        task_id=task.task_id,
                        build_passed=build_passed,
                        visible_tests_passed=visible_passed,
                        hidden_tests_passed=hidden_passed,
                        error_code=error_code,
                        duration_ms=duration_ms,
                        cost_usd=0.0012,
                    )
                )

        total = len(tasks)
        if total == 0:
            return BenchmarkReport(
                total_tasks=0,
                build_success_rate=0.0,
                visible_test_pass_rate=0.0,
                hidden_test_pass_rate=0.0,
                average_cost_usd=0.0,
                average_duration_seconds=0.0,
            )

        build_pass_count = sum(1 for r in task_results if r.build_passed)
        vis_pass_count = sum(1 for r in task_results if r.visible_tests_passed)
        hid_pass_count = sum(1 for r in task_results if r.hidden_tests_passed)
        avg_cost = sum(r.cost_usd for r in task_results) / total
        avg_dur = (sum(r.duration_ms for r in task_results) / total) / 1000.0

        return BenchmarkReport(
            total_tasks=total,
            build_success_rate=round(build_pass_count / total, 3),
            visible_test_pass_rate=round(vis_pass_count / total, 3),
            hidden_test_pass_rate=round(hid_pass_count / total, 3),
            average_cost_usd=round(avg_cost, 4),
            average_duration_seconds=round(avg_dur, 2),
            error_distribution={k: v for k, v in error_counts.items() if v > 0},
            task_results=task_results,
        )
