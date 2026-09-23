"""Unit tests for Atlassian Jira integration and ticket ingestion."""

import pytest
from fastapi.testclient import TestClient

from ai_java_engineer.api.app import app
from ai_java_engineer.integrations.jira_client import jira_client, JiraIssue

client = TestClient(app)


from ai_java_engineer.infrastructure.settings import AppSettings

def test_jira_client_list_issues():
    # Test demo / isolated mode
    demo_client = JiraClient(settings=AppSettings(jira_api_token=None, jira_url=None))
    issues = demo_client.list_assigned_issues()
    assert len(issues) >= 4
    keys = [i.key for i in issues]
    assert "PAY-104" in keys
    assert "AUTH-205" in keys
    assert "ORD-301" in keys
    assert "BUG-412" in keys

    # Test active client (live or fallback)
    active_issues = jira_client.list_assigned_issues()
    assert len(active_issues) >= 1



def test_jira_client_get_issue():
    issue = jira_client.get_issue("PAY-104")
    assert issue is not None
    assert issue.key == "PAY-104"
    assert "Reembolsos" in issue.summary
    assert len(issue.acceptance_criteria) >= 2


def test_jira_client_convert_to_requirement_spec():
    issue = jira_client.get_issue("AUTH-205")
    assert issue is not None
    req = jira_client.convert_to_requirement_spec(issue)
    assert req.id == "JIRA-AUTH-205"
    assert req.jira_key == "AUTH-205"
    assert "JWT" in req.title
    assert "OAuth2" in req.raw_text


def test_jira_client_transitions_and_comments():
    issue_key = "ORD-301"
    ok = jira_client.transition_issue(issue_key, "In Progress")
    assert ok is True
    issue = jira_client.get_issue(issue_key)
    assert issue.status == "In Progress"

    ok_comment = jira_client.add_comment(issue_key, "Test comment from QA Agent")
    assert ok_comment is True
    issue_after = jira_client.get_issue(issue_key)
    assert any("Test comment" in c.get("text", "") for c in issue_after.comments)


def test_api_list_jira_issues():
    res = client.get("/integrations/jira/issues")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 4


def test_api_get_jira_issue_by_key():
    res = client.get("/integrations/jira/issues/PAY-104")
    assert res.status_code == 200
    data = res.json()
    assert data["key"] == "PAY-104"
    assert "Reembolsos" in data["summary"]

    res_not_found = client.get("/integrations/jira/issues/NONEXISTENT-999")
    assert res_not_found.status_code == 404


def test_api_import_jira_issue():
    res = client.post("/integrations/jira/import/PAY-104", json={})
    assert res.status_code == 200
    data = res.json()
    assert "execution_id" in data
    assert data["jira_key"] == "PAY-104"
    assert "PAY-104" in data["title"]


def test_api_jira_webhook():
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "PAY-104",
            "fields": {
                "summary": "API de Procesamiento de Reembolsos",
                "description": "Detalle actualizado desde Jira Cloud",
                "issuetype": {"name": "Story"},
                "status": {"name": "To Do"},
                "priority": {"name": "High"},
                "assignee": {"displayName": "Java X"},
                "labels": ["payments", "agent-factory"],
            },
        },
    }
    res = client.post("/webhooks/jira", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "execution_id" in data
    assert data["jira_key"] == "PAY-104"
