"""Debug Agent: self-healing autonomous diagnosis and surgical patch generation."""

import hashlib
import re

from ai_java_engineer.domain.artifact import CodePlan
from ai_java_engineer.domain.execution import BuildResult, FailureFingerprint, TestResult
from ai_java_engineer.llm.base import ModelProvider, ModelRequest


class DebugAgent:
    """Diagnoses compilation and test failures and outputs surgical repair patches."""

    SYSTEM_PROMPT = (
        "You are an Elite Java / Maven Debugging Specialist. "
        "Analyze the provided Maven build failure or JUnit test failure output. "
        "Pinpoint the root cause (syntax error, missing import, type mismatch, broken assertion) "
        "and produce a surgical CodePlan containing only the necessary corrections. "
        "Never regenerate unaffected files."
    )

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @classmethod
    def compute_fingerprint(cls, error_text: str) -> FailureFingerprint:
        """Computes a deterministic SHA-256 fingerprint from compiler error text."""
        # Find file and line if available
        file_match = re.search(r"(/[\w/\.-]+\.java):\[(\d+),\d+\]", error_text)
        file_path = file_match.group(1) if file_match else None
        line_num = int(file_match.group(2)) if file_match else None

        # Normalize error text for fingerprinting
        clean_text = re.sub(r"\s+", " ", error_text).strip()
        fp_hash = hashlib.sha256(clean_text[:200].encode("utf-8")).hexdigest()[:16]

        return FailureFingerprint(
            fingerprint_hash=fp_hash,
            error_type="COMPILATION_ERROR" if "[ERROR]" in error_text else "TEST_FAILURE",
            file=file_path,
            line=line_num,
            summary=clean_text[:120],
        )

    async def execute(
        self,
        build_result: BuildResult | None,
        test_result: TestResult | None,
        failed_files_context: str,
    ) -> CodePlan:
        error_context = ""
        if build_result and not build_result.success:
            error_context = f"Maven Build Error:\n{build_result.stdout}\n{build_result.stderr}"
        elif test_result and not test_result.passed:
            failed_cases = [c for c in test_result.cases if c.status in ("FAILED", "ERROR")]
            error_context = "JUnit Test Failures:\n"
            for c in failed_cases[:5]:
                error_context += f"- {c.classname}.{c.name}: {c.failure_message}\n{c.stacktrace}\n"

        prompt = (
            f"=== ERROR DIAGNOSTICS ===\n{error_context}\n\n"
            f"=== CURRENT SOURCE FILES ===\n{failed_files_context}\n\n"
            f"Provide a surgical CodePlan correcting the specific failure above."
        )

        request = ModelRequest(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.05,
        )

        plan, _ = await self.provider.generate_structured(request, CodePlan)
        return plan
