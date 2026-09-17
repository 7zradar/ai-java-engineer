"""Security Agent: scans generated code for OWASP Top 10 vulnerabilities in Spring Boot."""

import re

from ai_java_engineer.domain.artifact import SecurityFinding, SecurityResult
from ai_java_engineer.llm.base import ModelProvider


class SecurityAgent:
    """Performs static analysis and security scanning on generated Java code."""

    STATIC_RULES = [
        (
            re.compile(r"createQuery\s*\(\s*['\"].*\+.*['\"]", re.IGNORECASE),
            "SQL_INJECTION",
            "CRITICAL",
            "Possible SQL Injection: dynamic string concatenation detected in JPA query.",
            "Use named parameters or Spring Data JPA derived query methods.",
        ),
        (
            re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
            "HARDCODED_SECRET",
            "HIGH",
            "Hardcoded credential detected in source file.",
            "Externalize secrets into application properties or environment variables.",
        ),
        (
            re.compile(r"@CrossOrigin\s*\(\s*['\"]?\*['\"]?\s*\)"),
            "PERMISSIVE_CORS",
            "MEDIUM",
            "Wildcard CORS allowed: potential unauthorized cross-origin access.",
            "Specify trusted origins explicitly.",
        ),
        (
            re.compile(r"\.csrf\(\)\.disable\(\)"),
            "CSRF_DISABLED",
            "MEDIUM",
            "CSRF protection is explicitly disabled.",
            "Keep CSRF enabled or ensure API is strictly stateless with bearer tokens.",
        ),
    ]

    def __init__(self, provider: ModelProvider | None = None):
        self.provider = provider

    def scan_statically(self, file_path: str, content: str) -> list[SecurityFinding]:
        """Runs fast, deterministic regex-based security checks."""
        findings: list[SecurityFinding] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            for pattern, cat, severity, desc, remed in self.STATIC_RULES:
                if pattern.search(line):
                    findings.append(
                        SecurityFinding(
                            severity=severity,  # type: ignore
                            category=cat,
                            file=file_path,
                            line=idx,
                            description=desc,
                            remediation=remed,
                        )
                    )

        return findings

    async def execute(self, files_to_scan: dict[str, str]) -> SecurityResult:
        all_findings: list[SecurityFinding] = []

        for file_path, content in files_to_scan.items():
            all_findings.extend(self.scan_statically(file_path, content))

        has_critical = any(f.severity == "CRITICAL" for f in all_findings)
        return SecurityResult(
            passed=(not has_critical),
            has_critical=has_critical,
            findings=all_findings,
        )
