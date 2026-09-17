"""Execution Backend protocol and command specifications."""

from typing import Protocol

from ai_java_engineer.domain.execution import BuildResult, TestResult


class ExecutionBackend(Protocol):
    """Abstract execution adapter decoupling Python orchestrator from Java/Maven runtime."""

    async def run_build(self, workspace_path: str, timeout_seconds: int = 300) -> BuildResult:
        """Executes 'mvn compile' or equivalent in an isolated environment."""
        ...

    async def run_tests(self, workspace_path: str, timeout_seconds: int = 300) -> TestResult:
        """Executes 'mvn test' and parses Surefire reports."""
        ...
