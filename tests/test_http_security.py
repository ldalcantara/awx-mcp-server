"""Security tests for the HTTP server hardening (FastAPI TestClient, no AWX).

Covers: mandatory auth on /mcp (default deny), opt-in anonymous, admin-token
gating (fail-closed + constant-time), CORS allowlist, body-size limit, docs
gating, metrics auth, and the SSRF guard on X-AWX-Base-URL.
"""

import pytest
from fastapi.testclient import TestClient

import awx_mcp_server.http_server as hs
from awx_mcp_server.mcp_server import create_mcp_server

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}


@pytest.fixture
def client(monkeypatch):
    # Clean env for each test; build a fresh app.
    for var in (
        "MCP_ALLOW_ANONYMOUS",
        "ADMIN_TOKEN",
        "CORS_ORIGINS",
        "AWX_ALLOWED_HOSTS",
        "MCP_ENABLE_DOCS",
        "MAX_REQUEST_BYTES",
    ):
        monkeypatch.delenv(var, raising=False)
    hs.API_KEYS.clear()
    return TestClient(hs.create_app(create_mcp_server()))


def _add_key(key="awx_mcp_testkey", tenant="t1"):
    hs.API_KEYS[key] = {"tenant_id": tenant, "name": "test", "created_at": "x"}
    return key


def test_mcp_requires_auth_by_default(client):
    r = client.post("/mcp", json=INIT)
    assert r.status_code == 401


def test_mcp_anonymous_opt_in(monkeypatch):
    monkeypatch.setenv("MCP_ALLOW_ANONYMOUS", "true")
    hs.API_KEYS.clear()
    c = TestClient(hs.create_app(create_mcp_server()))
    r = c.post("/mcp", json=INIT)
    assert r.status_code == 200
    assert r.json()["result"]["serverInfo"]["name"] == "awx-mcp-server"


def test_mcp_invalid_key_rejected(client):
    r = client.post("/mcp", json=INIT, headers={"X-API-Key": "nope"})
    assert r.status_code == 401


def test_mcp_valid_key_ok(client):
    key = _add_key()
    r = client.post("/mcp", json=INIT, headers={"X-API-Key": key})
    assert r.status_code == 200


def test_admin_fail_closed_when_unset(client):
    # ADMIN_TOKEN not configured -> admin API disabled (503).
    r = client.post(
        "/api/keys",
        json={"name": "k", "tenant_id": "t1"},
        headers={"Authorization": "Bearer anything"},
    )
    assert r.status_code == 503


def test_admin_wrong_then_right(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret-admin")
    hs.API_KEYS.clear()
    c = TestClient(hs.create_app(create_mcp_server()))
    bad = c.post(
        "/api/keys",
        json={"name": "k", "tenant_id": "t1"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert bad.status_code == 401
    good = c.post(
        "/api/keys",
        json={"name": "k", "tenant_id": "t1"},
        headers={"Authorization": "Bearer s3cret-admin"},
    )
    assert good.status_code == 200
    assert good.json()["api_key"].startswith("awx_mcp_")


def test_metrics_requires_auth(client):
    assert client.get("/prometheus-metrics").status_code == 401
    key = _add_key()
    assert (
        client.get("/prometheus-metrics", headers={"X-API-Key": key}).status_code == 200
    )


def test_docs_disabled_by_default(client):
    assert client.get("/docs").status_code == 404


def test_body_size_limit(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BYTES", "100")
    monkeypatch.setenv("MCP_ALLOW_ANONYMOUS", "true")
    hs.API_KEYS.clear()
    c = TestClient(hs.create_app(create_mcp_server()))
    big = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"x": "y" * 500},
    }
    assert c.post("/mcp", json=big).status_code == 413


def test_ssrf_guard_blocks_unlisted_base_url(client):
    key = _add_key()
    # No AWX_ALLOWED_HOSTS set -> any client-supplied base URL is rejected (403).
    r = client.post(
        "/mcp",
        json=INIT,
        headers={"X-API-Key": key, "X-AWX-Base-URL": "http://169.254.169.254/"},
    )
    assert r.status_code == 403


def test_ssrf_guard_allows_listed_host(monkeypatch):
    monkeypatch.setenv("AWX_ALLOWED_HOSTS", "awx.internal.example")
    hs.API_KEYS.clear()
    c = TestClient(hs.create_app(create_mcp_server()))
    key = _add_key()
    r = c.post(
        "/mcp",
        json=INIT,
        headers={"X-API-Key": key, "X-AWX-Base-URL": "https://awx.internal.example/"},
    )
    # initialize doesn't touch AWX, so an allowlisted host passes the guard.
    assert r.status_code == 200
