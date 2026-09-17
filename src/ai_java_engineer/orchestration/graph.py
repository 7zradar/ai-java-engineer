"""Deterministic State Machine Orchestrator for the engineering pipeline."""

from pathlib import Path
from typing import Any

from ai_java_engineer.agents.architect.architect_agent import ArchitectAgent
from ai_java_engineer.agents.coder.coding_agent import CodingAgent
from ai_java_engineer.agents.debugger.debug_agent import DebugAgent
from ai_java_engineer.agents.product.product_agent import ProductAgent
from ai_java_engineer.agents.reviewer.review_agent import ReviewAgent
from ai_java_engineer.agents.security.security_agent import SecurityAgent
from ai_java_engineer.domain.execution import RunStatus
from ai_java_engineer.execution.base import ExecutionBackend
from ai_java_engineer.infrastructure.logging import get_logger
from ai_java_engineer.llm.base import ModelProvider
from ai_java_engineer.orchestration.checkpoints import CheckpointStore
from ai_java_engineer.orchestration.state import EngineeringState
from ai_java_engineer.retrieval.context_builder import ContextBuilder
from ai_java_engineer.retrieval.repository_map import RepositoryScanner
from ai_java_engineer.tools.filesystem.secure_fs import (
    ReadFileInput,
    SecureFilesystem,
    WriteFileInput,
)
from ai_java_engineer.tools.git.git_service import GitService

logger = get_logger("orchestrator")


class EngineeringOrchestrator:
    """Coordinates the deterministic workflow across specialized agents and tools."""

    def __init__(
        self,
        provider: ModelProvider,
        backend: ExecutionBackend,
        checkpoint_store: CheckpointStore | None = None,
        require_human_pr_approval: bool = False,
    ):
        self.provider = provider
        self.backend = backend
        self.checkpoint_store = checkpoint_store or CheckpointStore()
        self.require_human_pr_approval = require_human_pr_approval

        # Agents
        self.product_agent = ProductAgent(provider)
        self.architect_agent = ArchitectAgent(provider)
        self.coding_agent = CodingAgent(provider)
        self.debug_agent = DebugAgent(provider)
        self.security_agent = SecurityAgent(provider)
        self.review_agent = ReviewAgent(provider)

    async def run(self, initial_state: EngineeringState) -> EngineeringState:
        """Executes the full state machine deterministically."""
        state = dict(initial_state)
        state.setdefault("status", RunStatus.RUNNING)
        state.setdefault("iteration", 0)
        state.setdefault("max_iterations", 3)
        state.setdefault("changed_files", [])
        state.setdefault("human_approved", False)

        ws_root = Path(state["workspace_path"]).resolve()
        fs = SecureFilesystem(ws_root)
        git = GitService(ws_root)

        # 1. Product Node
        logger.info("Executing Product Node", execution_id=state["execution_id"])
        state["product_spec"] = await self.product_agent.execute(state["requirement"])
        self._checkpoint("product_node", state)

        # 2. Repository Context Node
        logger.info("Indexing Repository", execution_id=state["execution_id"])
        state["repo_map"] = RepositoryScanner.scan(ws_root)
        ctx_builder = ContextBuilder(ws_root)
        state["repository_context"] = ctx_builder.build_context(state["repo_map"])
        self._checkpoint("context_node", state)

        # 3. Architect Node
        logger.info("Executing Architect Node", execution_id=state["execution_id"])
        state["architecture_spec"] = await self.architect_agent.execute(
            state["product_spec"], state["repository_context"]
        )
        self._checkpoint("architect_node", state)

        # 4. Coding Node
        logger.info("Executing Coding Node", execution_id=state["execution_id"])
        state["code_plan"] = await self.coding_agent.execute(
            state["product_spec"], state["architecture_spec"], state["repository_context"]
        )

        # Apply code plan to filesystem
        for action in state["code_plan"].actions:
            if action.action in ("CREATE", "MODIFY"):
                fs.write_file(WriteFileInput(path=action.path, content=action.content))
                if action.path not in state["changed_files"]:
                    state["changed_files"].append(action.path)

        self._checkpoint("coder_node", state)

        # 5. Build & Self-Healing Debug Loop
        while True:
            logger.info("Executing Build Node", iteration=state["iteration"])
            state["build_result"] = await self.backend.run_build(str(ws_root))

            if state["build_result"].success:
                logger.info("Build Passed")
                break

            # Build failed -> router check
            state["iteration"] += 1
            if state["iteration"] > state["max_iterations"]:
                logger.warn("Max debug iterations reached, escalating")
                state["status"] = RunStatus.FAILED
                state["escalation_reason"] = "Exceeded max build debug iterations."
                self._checkpoint("escalation_node", state)
                return state

            logger.info("Triggering Debug Agent for compilation error", iteration=state["iteration"])
            # Read current content of failing files
            failing_context = ""
            for cf in state["changed_files"]:
                try:
                    f_out = fs.read_file(ReadFileInput(path=cf))
                    failing_context += f"--- {cf} ---\n{f_out.content}\n"
                except Exception:
                    continue

            debug_plan = await self.debug_agent.execute(
                state["build_result"], None, failing_context
            )
            for action in debug_plan.actions:
                fs.write_file(WriteFileInput(path=action.path, content=action.content))

            self._checkpoint(f"debug_node_iter_{state['iteration']}", state)

        # 6. Test Node
        logger.info("Executing Test Node", execution_id=state["execution_id"])
        state["test_result"] = await self.backend.run_tests(str(ws_root))
        self._checkpoint("test_node", state)

        # 7. Security Node
        logger.info("Executing Security Node", execution_id=state["execution_id"])
        files_to_scan = {}
        for cf in state["changed_files"]:
            try:
                out = fs.read_file(ReadFileInput(path=cf))
                files_to_scan[cf] = out.content
            except Exception:
                continue

        state["security_result"] = await self.security_agent.execute(files_to_scan)
        if state["security_result"].has_critical:
            logger.error("Critical security finding detected! Halting pipeline.")
            state["status"] = RunStatus.SECURITY_BLOCKED
            state["escalation_reason"] = "Critical security vulnerability detected."
            self._checkpoint("security_blocked_node", state)
            return state

        self._checkpoint("security_node", state)

        # 8. Review Node
        logger.info("Executing Review Node", execution_id=state["execution_id"])
        state["git_diff"] = git.get_diff()
        state["review_result"] = await self.review_agent.execute(
            state["product_spec"],
            state["architecture_spec"],
            state["git_diff"],
            state["test_result"],
            state["security_result"],
        )
        self._checkpoint("review_node", state)

        # 9. Human Approval Gate
        if self.require_human_pr_approval and not state.get("human_approved"):
            logger.info("Waiting for human PR approval gate")
            state["status"] = RunStatus.WAITING_APPROVAL
            self._checkpoint("waiting_approval_node", state)
            return state

        # 10. Git PR Delivery Node
        logger.info("Executing Git PR Delivery Node", execution_id=state["execution_id"])
        branch_name = f"feat/ai-{state['requirement'].id.lower()}"
        git.create_feature_branch(branch_name)
        git.commit_changes(f"feat: {state['product_spec'].title}", state["changed_files"])

        test_summary = (
            f"Passed: {state['test_result'].passed_count}/{state['test_result'].total} "
            f"(Duration: {state['test_result'].duration_ms}ms)"
        )
        state["pr_payload"] = git.build_pr_payload(
            branch_name=branch_name,
            base_branch=state["requirement"].branch_base,
            product_spec=state["product_spec"],
            test_summary=test_summary,
        )

        state["status"] = RunStatus.COMPLETED
        self._checkpoint("completed_node", state)
        logger.info("Pipeline Completed Successfully", execution_id=state["execution_id"])

        return state

    def _checkpoint(self, node_name: str, state: dict[str, Any]) -> None:
        if self.checkpoint_store:
            self.checkpoint_store.save_checkpoint(
                execution_id=state["execution_id"],
                node_name=node_name,
                status=state["status"],
                state=state,
            )
