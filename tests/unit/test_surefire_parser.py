"""Unit tests for Maven Surefire XML parsing."""

import tempfile
from pathlib import Path

from ai_java_engineer.execution.parsers.surefire_parser import SurefireParser

SAMPLE_SUREFIRE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" name="com.example.OrderControllerTest" time="0.125" tests="2" errors="0" skipped="0" failures="1">
  <testcase name="testCreateOrderSuccess" classname="com.example.OrderControllerTest" time="0.080"/>
  <testcase name="testGetOrderNotFound" classname="com.example.OrderControllerTest" time="0.045">
    <failure message="expected: &lt;404&gt; but was: &lt;500&gt;" type="org.opentest4j.AssertionFailedError">org.opentest4j.AssertionFailedError: expected: 404 but was: 500
      at com.example.OrderControllerTest.testGetOrderNotFound(OrderControllerTest.java:34)
    </failure>
  </testcase>
</testsuite>
"""


def test_surefire_parser_parsing():
    with tempfile.TemporaryDirectory() as temp_dir:
        xml_file = Path(temp_dir) / "TEST-com.example.OrderControllerTest.xml"
        xml_file.write_text(SAMPLE_SUREFIRE_XML, encoding="utf-8")

        result = SurefireParser.parse_directory(temp_dir)
        assert result.total == 2
        assert result.passed_count == 1
        assert result.failed_count == 1
        assert result.passed is False
        assert len(result.cases) == 2

        failed_case = next(c for c in result.cases if c.status == "FAILED")
        assert failed_case.name == "testGetOrderNotFound"
        assert "404" in failed_case.failure_message
