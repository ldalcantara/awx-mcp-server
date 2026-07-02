"""Tests for connection reuse across tool calls.

Building a fresh CompositeAWXClient (and with it a fresh httpx.AsyncClient)
on every tool call costs a full TCP+TLS handshake per call. The server now
caches one client per resolved (URL, credentials) and marks it ``persistent``
so the per-handler ``async with client`` blocks don't close it.
"""

import uuid

from unittest.mock import AsyncMock

from awx_mcp_server.clients.composite_client import CompositeAWXClient
from awx_mcp_server.domain import EnvironmentConfig, NoActiveEnvironmentError
from awx_mcp_server.http_server import process_mcp_message
from awx_mcp_server.mcp_server import create_mcp_server


def _env():
    return EnvironmentConfig(
        env_id=str(uuid.uuid4()),
        name="test",
        base_url="https://awx.example/",
        verify_ssl=True,
    )


async def test_context_exit_closes_default_client():
    """Without the persistent flag, leaving async-with closes the pool."""
    client = CompositeAWXClient(_env(), "u", "p")
    async with client:
        pass
    assert client.rest_client.client.is_closed


async def test_context_exit_keeps_persistent_client_open():
    """A cache-owned client survives async-with; aclose() really closes it."""
    client = CompositeAWXClient(_env(), "u", "p")
    client.persistent = True
    async with client:
        pass
    assert not client.rest_client.client.is_closed
    await client.aclose()
    assert client.rest_client.client.is_closed


class _FakeClient:
    """Async-context-manager stand-in for CompositeAWXClient."""

    def __init__(self):
        self.list_workflow_job_templates = AsyncMock(return_value=[])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _prepare_server(monkeypatch):
    monkeypatch.setenv("AWX_BASE_URL", "http://awx.test")
    monkeypatch.delenv("AWX_TOKEN", raising=False)
    monkeypatch.setenv("AWX_USERNAME", "u")
    monkeypatch.setenv("AWX_PASSWORD", "p")

    class _NoStoredConfig:
        def __init__(self, *a, **k):
            pass

        def get_active(self):
            raise NoActiveEnvironmentError("no stored env in test")

    monkeypatch.setattr("awx_mcp_server.mcp_server.ConfigManager", _NoStoredConfig)
    return create_mcp_server()


async def _call(server, name="awx_workflow_templates_list"):
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": {}},
    }
    return await process_mcp_message(server, msg, "test-tenant")


async def test_tool_calls_reuse_cached_client(monkeypatch):
    """Two tool calls with the same credentials build the client only once."""
    server = _prepare_server(monkeypatch)
    built = []

    def factory(*a, **k):
        client = _FakeClient()
        built.append(client)
        return client

    monkeypatch.setattr("awx_mcp_server.mcp_server.CompositeAWXClient", factory)
    await _call(server)
    await _call(server)

    assert len(built) == 1, "client should be constructed once, then reused"
    assert built[0].list_workflow_job_templates.await_count == 2
    assert built[0].persistent is True


async def test_distinct_credentials_get_distinct_clients(monkeypatch):
    """Changing the resolved credentials yields a different cached client."""
    server = _prepare_server(monkeypatch)
    built = []

    def factory(*a, **k):
        client = _FakeClient()
        built.append(client)
        return client

    monkeypatch.setattr("awx_mcp_server.mcp_server.CompositeAWXClient", factory)
    await _call(server)
    monkeypatch.setenv("AWX_PASSWORD", "rotated")
    await _call(server)

    assert len(built) == 2, "new credentials must not reuse the old client"
