"""Deterministic State Machine Orchestrator for the engineering pipeline."""

from pathlib import Path
from typing import Any

from ai_java_engineer.agents.architect.architect_agent import ArchitectAgent
from ai_java_engineer.agents.coder.coding_agent import CodingAgent
from ai_java_engineer.agents.debugger.debug_agent import DebugAgent
from ai_java_engineer.agents.product.product_agent import ProductAgent
from ai_java_engineer.agents.qa.qa_agent import QAAgent
from ai_java_engineer.agents.reviewer.review_agent import ReviewAgent
from ai_java_engineer.agents.security.security_agent import SecurityAgent
from ai_java_engineer.domain.architecture import ArchitectureSpec, EndpointSpec, ComponentSpec
from ai_java_engineer.domain.artifact import CodePlan, SecurityResult, ReviewResult
from ai_java_engineer.domain.execution import RunStatus
from ai_java_engineer.domain.requirement import ProductSpec, UserStory, AcceptanceCriterion, RequirementSpec
from ai_java_engineer.execution.base import ExecutionBackend
from ai_java_engineer.infrastructure.logging import get_logger
from ai_java_engineer.llm.base import ModelProvider
from ai_java_engineer.orchestration.checkpoints import CheckpointStore
from ai_java_engineer.orchestration.state import EngineeringState
from ai_java_engineer.retrieval.context_builder import ContextBuilder
from ai_java_engineer.retrieval.knowledge_store import CorporateKnowledgeStore
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
        self.knowledge_store = CorporateKnowledgeStore()

        # Agents
        self.product_agent = ProductAgent(provider)
        self.architect_agent = ArchitectAgent(provider)
        self.coding_agent = CodingAgent(provider)
        self.qa_agent = QAAgent(provider)
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

        # If already approved by human, proceed directly to Git PR delivery and GitHub push
        if state.get("human_approved"):
            logger.info("Human approval granted. Proceeding directly to Git PR Delivery Node.", execution_id=state["execution_id"])
            return self._deliver_pr(state, git)

        mode = state.get("execution_mode") or "full_pipeline"
        selected_agents = list(state.get("selected_agents") or [])
        if not selected_agents:
            if mode == "coder_only":
                selected_agents = ["coder"]
            elif mode == "qa_only":
                selected_agents = ["qa"]
            elif mode == "architect_only":
                selected_agents = ["product", "architect"]
            else:
                selected_agents = ["product", "architect", "coder", "qa", "security", "review"]
        state["selected_agents"] = selected_agents

        # 1. Product Node
        req = state.get("requirement")
        if isinstance(req, dict):
            state["requirement"] = RequirementSpec.model_validate(req)

        if "product" in selected_agents:
            logger.info("Executing Product Node", execution_id=state["execution_id"])
            state["product_spec"] = await self.product_agent.execute(state["requirement"])
            self._checkpoint("product_node", state)
        else:
            logger.info(f"Selective mode: Skipping Product Node for token saving", execution_id=state["execution_id"])
            state["product_spec"] = ProductSpec(
                title=state["requirement"].title,
                summary=state["requirement"].raw_text[:250],
                user_stories=[UserStory(id="US-001", title=state["requirement"].title, as_a="Usuario", i_want="utilizar esta funcionalidad", so_that="cumpla el requerimiento")],
                acceptance_criteria=[AcceptanceCriterion(id="AC-001", scenario="Ejecución exitosa", given="Entorno activo", when="Se invoca el servicio", then="Responde código 200 OK")]
            )

        # 2. Repository Context Node & Corporate Standards RAG
        logger.info("Indexing Repository & Loading Corporate Knowledge", execution_id=state["execution_id"])
        state["repo_map"] = RepositoryScanner.scan(ws_root)
        ctx_builder = ContextBuilder(ws_root)
        repo_ctx = ctx_builder.build_context(state["repo_map"])
        guidelines = self.knowledge_store.get_guidelines_text(["security", "spring-boot", "jpa", "rest"])
        state["corporate_guidelines"] = guidelines
        state["repository_context"] = f"{repo_ctx}\n\n{guidelines}" if guidelines else repo_ctx
        self._checkpoint("context_node", state)

        # 3. Architect Node
        if "architect" in selected_agents:
            logger.info("Executing Architect Node", execution_id=state["execution_id"])
            state["architecture_spec"] = await self.architect_agent.execute(
                state["product_spec"], state["repository_context"]
            )
            self._checkpoint("architect_node", state)
        else:
            logger.info(f"Selective mode: Skipping Architect Node for token saving", execution_id=state["execution_id"])
            state["architecture_spec"] = ArchitectureSpec(
                summary="Arquitectura directa generada para desarrollo rápido",
                endpoints=[
                    EndpointSpec(
                        method="GET",
                        path="/api/v1/resource",
                        description="Endpoint directo generado para modo desarrollador",
                        response_dto="ResourceResponse",
                        status_code=200,
                    )
                ],
                components=[
                    ComponentSpec(
                        package="com.example.app.service",
                        name="DirectService",
                        component_type="SERVICE",
                        description="Lógica de negocio directa",
                    )
                ],
            )

        if "coder" not in selected_agents and "qa" not in selected_agents:
            logger.info("Architect/Product Only mode completed. Stopping pipeline.", execution_id=state["execution_id"])
            state["status"] = RunStatus.COMPLETED
            return state

        # 4. Coding Node
        if "coder" in selected_agents:
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
        else:
            logger.info("Selective mode: Skipping Coding Node by user configuration", execution_id=state["execution_id"])
            state["code_plan"] = CodePlan(summary="Plan directo para QA testing", actions=[])

        # 5. QA Node (Independent Quality Assurance Subagent)
        if "qa" in selected_agents:
            logger.info("Executing QA Node", execution_id=state["execution_id"])
            state["qa_plan"] = await self.qa_agent.execute(
                state["product_spec"], state["architecture_spec"], state["code_plan"]
            )
            # Apply QA test plan to filesystem
            for action in state["qa_plan"].actions:
                if action.action in ("CREATE", "MODIFY"):
                    fs.write_file(WriteFileInput(path=action.path, content=action.content))
                    if action.path not in state["changed_files"]:
                        state["changed_files"].append(action.path)
            self._checkpoint("qa_node", state)
        else:
            logger.info("Selective mode: Skipping QA Node by user configuration", execution_id=state["execution_id"])

        # If no code was generated, finish early
        if not state["changed_files"]:
            logger.info("No files modified by selected agents. Completing run.", execution_id=state["execution_id"])
            state["status"] = RunStatus.COMPLETED
            return state

        # 6. Build & Self-Healing Debug Loop
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

        # 7. Security Node & 8. Review Node
        if "security" in selected_agents:
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
        else:
            logger.info("Selective mode: Skipping Security Guard to maximize token savings.", execution_id=state["execution_id"])
            state["security_result"] = SecurityResult(passed=True, has_critical=False, findings=[])

        if "review" in selected_agents:
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
        else:
            logger.info("Selective mode: Skipping Review Agent to maximize token savings.", execution_id=state["execution_id"])
            state["review_result"] = ReviewResult(
                verdict="APPROVED",
                score=1.0,
                summary=f"Modo selectivo ({', '.join(selected_agents)}): Ejecución focalizada exitosa sin overhead de tokens.",
                checklist=[]
            )

        # 9. Human Approval Gate
        if self.require_human_pr_approval and not state.get("human_approved"):
            logger.info("Waiting for human PR approval gate")
            state["status"] = RunStatus.WAITING_APPROVAL
            self._checkpoint("waiting_approval_node", state)
            return state

        # 10. Git PR Delivery Node
        return self._deliver_pr(state, git)

    def _deliver_pr(self, state: EngineeringState, git: GitService) -> EngineeringState:
        """Executes Git PR Delivery Node: commits changes and pushes branch to GitHub remote."""
        logger.info("Executing Git PR Delivery Node", execution_id=state["execution_id"])
        jira_key = state.get("jira_key")
        if jira_key:
            task_ref = str(jira_key).lower()
        else:
            req = state.get("requirement")
            req_id = getattr(req, "id", None) or (req.get("id") if isinstance(req, dict) else "") or state["execution_id"]
            task_ref = str(req_id).replace("JIRA-", "").replace("RUN-", "").lower()
        branch_name = f"feat/ai-{task_ref}"

        test_res = state.get("test_result")
        passed_cnt = getattr(test_res, "passed_count", None) if test_res else 0
        if passed_cnt is None and isinstance(test_res, dict):
            passed_cnt = test_res.get("passed_count", 0)
        total_cnt = getattr(test_res, "total", None) if test_res else 0
        if total_cnt is None and isinstance(test_res, dict):
            total_cnt = test_res.get("total", 0)
        duration_ms = getattr(test_res, "duration_ms", None) if test_res else 0
        if duration_ms is None and isinstance(test_res, dict):
            duration_ms = test_res.get("duration_ms", 0)

        test_summary = f"Passed: {passed_cnt}/{total_cnt} (Duration: {duration_ms}ms)"

        req = state.get("requirement")
        base_branch = getattr(req, "branch_base", None) or (req.get("branch_base") if isinstance(req, dict) else "main") or "main"

        prod_spec = state.get("product_spec")
        spec_title = getattr(prod_spec, "title", None) or (prod_spec.get("title") if isinstance(prod_spec, dict) else "Automated Feature") or "Automated Feature"

        pr_payload = git.build_pr_payload(
            branch_name=branch_name,
            base_branch=base_branch,
            product_spec=prod_spec,
            test_summary=test_summary,
        )

        push_res = git.push_approved_feature_to_remote(
            branch_name=branch_name,
            commit_message=f"feat: {spec_title}",
            files=state.get("changed_files"),
        )
        state["github_remote"] = push_res
        if push_res.get("pr_url"):
            pr_payload.pr_url = push_res["pr_url"]
        if push_res.get("branch_url"):
            pr_payload.branch_url = push_res["branch_url"]

        state["pr_payload"] = pr_payload
        state["status"] = RunStatus.COMPLETED
        self._checkpoint("completed_node", state)
        logger.info(
            "Pipeline Completed Successfully",
            execution_id=state["execution_id"],
            branch=branch_name,
            pr_url=pr_payload.pr_url,
        )

        return state

    def _checkpoint(self, node_name: str, state: dict[str, Any]) -> None:
        if self.checkpoint_store:
            self.checkpoint_store.save_checkpoint(
                execution_id=state["execution_id"],
                node_name=node_name,
                status=state["status"],
                state=state,
            )
