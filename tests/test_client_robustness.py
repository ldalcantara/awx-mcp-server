"""Client-robustness regression tests (no live AWX).

Covers: awxkit/REST extra_vars shape alignment, and the composite client
logging (no longer silently swallowing) its CLI->REST fallback.
"""

import uuid

from unittest.mock import AsyncMock

from awx_mcp_server.clients import composite_client as cc
from awx_mcp_server.clients.awxkit_client import AwxkitClient
from awx_mcp_server.clients.composite_client import CompositeAWXClient
from awx_mcp_server.domain import EnvironmentConfig


def _env():
    return EnvironmentConfig(
        env_id=str(uuid.uuid4()),
        name="t",
        base_url="https://awx.test/",
        verify_ssl=True,
    )


async def test_awxkit_parses_json_string_extra_vars():
    """awxkit must normalize a JSON-string extra_vars to a dict, like REST
    (previously it leaked the raw string through)."""
    client = AwxkitClient(_env(), "u", "p")
    client._run_cli = AsyncMock(
        return_value={
            "id": 1,
            "name": "t",
            "project": 1,
            "playbook": "p.yml",
            "extra_vars": '{"env": "prod"}',
        }
    )
    jt = await client.get_job_template(1)
    assert jt.extra_vars == {"env": "prod"}


async def test_composite_logs_and_falls_back(monkeypatch):
    """When the CLI path fails, the composite must fall back to REST AND log
    the failure (it used to be a silent `except Exception: pass`)."""
    warnings = []
    monkeypatch.setattr(cc.logger, "warning", lambda *a, **k: warnings.append((a, k)))

    client = CompositeAWXClient(_env(), "u", "p")
    client.prefer_cli = True
    client.cli_client.list_job_templates = AsyncMock(
        side_effect=RuntimeError("awx binary not found")
    )
    rest_result = ["sentinel-from-rest"]  # composite returns it verbatim
    client.rest_client.list_job_templates = AsyncMock(return_value=rest_result)

    result = await client.list_job_templates()
    assert result == rest_result  # fell back to REST
    client.cli_client.list_job_templates.assert_awaited_once()  # CLI was tried
    assert warnings, "fallback must be logged, not silently swallowed"
