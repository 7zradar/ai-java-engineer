"""Safe Maven Surefire XML report parser for JUnit 5 test executions."""

import xml.etree.ElementTree as ET
from pathlib import Path

from ai_java_engineer.domain.execution import TestCaseResult, TestResult


class SurefireParser:
    """Parses standard Surefire XML files into structured TestResult models."""

    @classmethod
    def parse_file(cls, xml_path: str | Path) -> list[TestCaseResult]:
        path = Path(xml_path)
        if not path.exists():
            return []

        tree = ET.parse(str(path))
        root = tree.getroot()

        results = []
        for tc in root.findall(".//testcase"):
            classname = tc.attrib.get("classname", "UnknownClass")
            name = tc.attrib.get("name", "unknownMethod")
            time_val = float(tc.attrib.get("time", 0.0))

            failure_el = tc.find("failure")
            error_el = tc.find("error")
            skipped_el = tc.find("skipped")

            if failure_el is not None:
                status = "FAILED"
                failure_msg = failure_el.attrib.get("message", "")
                stacktrace = failure_el.text or ""
            elif error_el is not None:
                status = "ERROR"
                failure_msg = error_el.attrib.get("message", "")
                stacktrace = error_el.text or ""
            elif skipped_el is not None:
                status = "SKIPPED"
                failure_msg = None
                stacktrace = None
            else:
                status = "PASSED"
                failure_msg = None
                stacktrace = None

            results.append(
                TestCaseResult(
                    classname=classname,
                    name=name,
                    time=time_val,
                    status=status,
                    failure_message=failure_msg,
                    stacktrace=stacktrace,
                )
            )

        return results

    @classmethod
    def parse_directory(cls, reports_dir: str | Path) -> TestResult:
        dir_path = Path(reports_dir)
        cases: list[TestCaseResult] = []

        if dir_path.exists() and dir_path.is_dir():
            for xml_file in dir_path.glob("TEST-*.xml"):
                try:
                    cases.extend(cls.parse_file(xml_file))
                except Exception:
                    continue

        total = len(cases)
        passed_count = sum(1 for c in cases if c.status == "PASSED")
        failed_count = sum(1 for c in cases if c.status in ("FAILED", "ERROR"))
        skipped_count = sum(1 for c in cases if c.status == "SKIPPED")
        total_time_ms = int(sum(c.time for c in cases) * 1000)

        return TestResult(
            passed=(failed_count == 0 and total > 0),
            total=total,
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            duration_ms=total_time_ms,
            cases=cases,
        )
