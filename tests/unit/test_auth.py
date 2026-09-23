"""Unit tests for Authentication and Role-Based Access Control (RBAC)."""

import pytest
from fastapi.testclient import TestClient
from ai_java_engineer.api.app import app, USERS_CATALOG

client = TestClient(app)

def test_login_admin_success():
    response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "lead_architect"
    assert "approve_pr" in data["user"]["permissions"]

def test_login_invalid_password():
    response = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"]

def test_login_all_demo_roles():
    roles = [
        ("admin", "admin"),
        ("diego", "diego"),
        ("diego", "diego123"),
        ("lorena", "lorena"),
        ("lorena", "lorena123"),
        ("dev", "dev"),
        ("dev", "dev123"),
        ("auditor", "auditor"),
        ("auditor", "auditor123"),
    ]
    for username, password in roles:
        res = client.post("/auth/login", json={"username": username, "password": password})
        assert res.status_code == 200
        user = res.json()["user"]
        assert user["username"] == username

def test_auth_me_and_logout():
    # Login as lorena
    res = client.post("/auth/login", json={"username": "lorena", "password": "lorena123"})
    token = res.json()["token"]

    # Check /auth/me
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "operations_director"
    assert "approve_pr" not in me_res.json()["permissions"]

    # Logout
    out_res = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out_res.status_code == 200

    # /auth/me after logout should fail
    me_after = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401

def test_get_roles_list():
    res = client.get("/auth/roles")
    assert res.status_code == 200
    roles = res.json()
    assert len(roles) >= 5
    usernames = [r["username"] for r in roles]
    assert "admin" in usernames
    assert "diego" in usernames
    assert "lorena" in usernames
    assert "dev" in usernames
    assert "auditor" in usernames
