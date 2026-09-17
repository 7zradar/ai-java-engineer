"""Deterministic Local Mock Execution Backend for offline development and testing."""

import hashlib
from pathlib import Path

from ai_java_engineer.domain.execution import (
    BuildResult,
    FailureFingerprint,
    TestCaseResult,
    TestResult,
)
from ai_java_engineer.execution.base import ExecutionBackend


class LocalMockBackend(ExecutionBackend):
    """Simulates Java 21 + Maven compilation and JUnit execution without Java installed locally."""

    def __init__(self, fail_first_build: bool = False):
        self.fail_first_build = fail_first_build
        self.build_attempts = 0

    async def run_build(self, workspace_path: str, timeout_seconds: int = 300) -> BuildResult:
        self.build_attempts += 1
        ws = Path(workspace_path)

        # Check if any .java files contain intentional syntax error or if configured to fail once
        java_files = list(ws.glob("**/*.java")) if ws.exists() else []
        has_syntax_error = False
        error_file = ""
        error_line = 1

        for jf in java_files:
            content = jf.read_text(encoding="utf-8", errors="replace")
            if "SYNTAX_ERROR" in content or "MISSING_SEMICOLON" in content:
                has_syntax_error = True
                error_file = str(jf.relative_to(ws)).replace("\\", "/")
                break

        if self.fail_first_build and self.build_attempts == 1 or has_syntax_error:
            msg = "[ERROR] /src/main/java/OrderController.java:[14,35] ';' expected"
            fp_hash = hashlib.sha256(msg.encode()).hexdigest()[:16]
            return BuildResult(
                success=False,
                exit_code=1,
                stdout="[INFO] Scanning for projects...\n[INFO] Compiling 2 source files to /target/classes\n" + msg,
                stderr="Compilation failure",
                duration_ms=450,
                error_summary="Compilation failure: ';' expected",
                fingerprint=FailureFingerprint(
                    fingerprint_hash=fp_hash,
                    error_type="COMPILATION_ERROR",
                    file=error_file or "src/main/java/OrderController.java",
                    line=error_line or 14,
                    summary="Syntax error: missing semicolon",
                ),
            )

        return BuildResult(
            success=True,
            exit_code=0,
            stdout="[INFO] BUILD SUCCESS\n[INFO] Total time: 1.250 s\n[INFO] Finished at: 2026-09-17T01:50:00Z",
            stderr="",
            duration_ms=1250,
            error_summary=None,
            fingerprint=None,
        )

    async def run_tests(self, workspace_path: str, timeout_seconds: int = 300) -> TestResult:
        ws = Path(workspace_path)
        test_files = list(ws.glob("**/src/test/**/*.java")) if ws.exists() else []
        total_cases = max(len(test_files), 1)

        cases = [
            TestCaseResult(
                classname="com.example.demo.controller.OrderControllerTest",
                name="testGetOrdersSuccess",
                time=0.045,
                status="PASSED",
            )
        ]

        return TestResult(
            passed=True,
            total=total_cases,
            passed_count=total_cases,
            failed_count=0,
            skipped_count=0,
            duration_ms=150,
            cases=cases,
            stdout_ref="Tests run: 1, Failures: 0, Errors: 0, Skipped: 0",
        )
