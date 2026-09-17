"""Remote CI Execution Backend dispatching Java 21 + Maven builds to external runners."""

import hashlib

import httpx

from ai_java_engineer.domain.execution import BuildResult, FailureFingerprint, TestResult
from ai_java_engineer.execution.base import ExecutionBackend
from ai_java_engineer.execution.parsers.surefire_parser import SurefireParser
from ai_java_engineer.infrastructure.errors import ExecutionBackendError


class RemoteCiExecutionBackend(ExecutionBackend):
    """Executes builds remotely via webhook / HTTP endpoint or GitHub Actions runner."""

    def __init__(
        self,
        endpoint_url: str,
        auth_token: str | None = None,
        timeout_seconds: int = 600,
    ):
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        self.timeout_seconds = timeout_seconds

    async def run_build(self, workspace_path: str, timeout_seconds: int = 300) -> BuildResult:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        payload = {
            "command": "mvn compile",
            "workspace_path": workspace_path,
            "timeout": timeout_seconds or self.timeout_seconds,
        }

        try:
            async with httpx.AsyncClient(timeout=float(timeout_seconds or self.timeout_seconds)) as client:
                resp = await client.post(f"{self.endpoint_url}/build", json=payload, headers=headers)
                if resp.status_code != 200:
                    raise ExecutionBackendError(
                        f"Remote CI build invocation failed with code {resp.status_code}: {resp.text}"
                    )
                data = resp.json()
        except Exception as ex:
            raise ExecutionBackendError(f"Failed to communicate with remote CI runner: {ex}") from ex

        success = data.get("exit_code", 1) == 0
        stdout = data.get("stdout", "")
        fp = None
        if not success:
            fp_hash = hashlib.sha256(stdout.encode()).hexdigest()[:16]
            fp = FailureFingerprint(
                fingerprint_hash=fp_hash,
                error_type="COMPILATION_ERROR",
                summary="Remote Maven compilation failure",
            )

        return BuildResult(
            success=success,
            exit_code=data.get("exit_code", 1),
            stdout=stdout,
            stderr=data.get("stderr", ""),
            duration_ms=data.get("duration_ms", 0),
            error_summary=data.get("error_summary"),
            fingerprint=fp,
        )

    async def run_tests(self, workspace_path: str, timeout_seconds: int = 300) -> TestResult:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        payload = {
            "command": "mvn test",
            "workspace_path": workspace_path,
            "timeout": timeout_seconds or self.timeout_seconds,
        }

        try:
            async with httpx.AsyncClient(timeout=float(timeout_seconds or self.timeout_seconds)) as client:
                resp = await client.post(f"{self.endpoint_url}/test", json=payload, headers=headers)
                if resp.status_code != 200:
                    raise ExecutionBackendError(f"Remote CI test invocation failed: {resp.text}")
                data = resp.json()
        except Exception as ex:
            raise ExecutionBackendError(f"Remote CI runner unreachable: {ex}") from ex

        # Parse test reports if XML payloads returned
        cases = []
        if "surefire_xml" in data:
            # Parse XML directly from payload
            cases = SurefireParser.parse_file(data["surefire_xml"])

        passed = data.get("exit_code", 1) == 0 and data.get("failed_count", 0) == 0
        return TestResult(
            passed=passed,
            total=data.get("total", 0),
            passed_count=data.get("passed_count", 0),
            failed_count=data.get("failed_count", 0),
            skipped_count=data.get("skipped_count", 0),
            duration_ms=data.get("duration_ms", 0),
            cases=cases,
            stdout_ref=data.get("stdout", ""),
        )
