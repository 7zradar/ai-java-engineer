"""Command-line script to run an End-to-End Pilot execution."""

import asyncio
import tempfile
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_java_engineer.domain.requirement import RequirementSpec
from ai_java_engineer.execution.local_mock import LocalMockBackend
from ai_java_engineer.infrastructure.logging import configure_logging
from ai_java_engineer.llm.providers.mock_provider import MockProvider
from ai_java_engineer.observability.tracing import ExecutionTracer
from ai_java_engineer.orchestration.graph import EngineeringOrchestrator
from ai_java_engineer.orchestration.state import EngineeringState

configure_logging()


async def main():
    print("================================================================")
    print("       AI JAVA ENGINEER - END-TO-END PILOT EXECUTION           ")
    print("================================================================")

    with tempfile.TemporaryDirectory() as temp_dir:
        provider = MockProvider()
        # Simulate compilation failure on 1st attempt to demonstrate self-healing debug loop
        backend = LocalMockBackend(fail_first_build=True)
        tracer = ExecutionTracer("PILOT-RUN-001")

        orchestrator = EngineeringOrchestrator(
            provider=provider,
            backend=backend,
            require_human_pr_approval=False,
        )

        requirement = RequirementSpec(
            id="FEAT-101",
            title="Customer Order History API",
            raw_text="Expose GET /api/v1/customers/{id}/orders with pagination and status filters (PENDING, SHIPPED).",
            target_repository=temp_dir,
            constraints=["Spring Boot 3.3", "Java 21", "Pure JUnit 5 unit tests"],
        )

        initial_state: EngineeringState = {
            "execution_id": "PILOT-RUN-001",
            "workspace_path": temp_dir,
            "requirement": requirement,
        }

        span = tracer.start_span("pilot_run")
        print("\n[1/7] Ingesting Requirement & Running Product Agent...")
        state = await orchestrator.run(initial_state)
        tracer.end_span(span, status=state["status"].value)

        print("\n[+] Execution Completed with Status:", state["status"].value)
        print("[+] Product Spec Title:", state["product_spec"].title)
        print("[+] Architecture Endpoints:", [e.path for e in state["architecture_spec"].endpoints])
        print("[+] Changed Files Generated:", state["changed_files"])
        print(f"[+] Debug Loop Iterations Executed: {state['iteration']} (Self-healing succeeded)")
        print("[+] Build Status:", "SUCCESS" if state["build_result"].success else "FAILED")
        print(f"[+] Tests Passed: {state['test_result'].passed_count}/{state['test_result'].total}")
        print("[+] Security Scan Passed:", state["security_result"].passed)
        print("[+] Review Verdict:", state["review_result"].verdict)
        print("\n[+] Generated PR Payload:")
        print(f"    Branch: {state['pr_payload'].branch}")
        print(f"    Title:  {state['pr_payload'].title}")
        print("----------------------------------------------------------------")
        print("PR Description Preview:\n")
        print(state['pr_payload'].body[:300] + "...\n")
        print("================================================================")


if __name__ == "__main__":
    asyncio.run(main())
