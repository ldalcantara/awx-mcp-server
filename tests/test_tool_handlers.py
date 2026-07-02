"""Mocked unit tests for MCP tool handlers (no live AWX).

The big coverage gap was that none of the tool handlers in ``call_tool`` had
assertion-based tests — including the write-capable workflow/notification tools
added by connor-griffin5. These tests drive each handler end-to-end through
``process_mcp_message`` with a fake AWX client, asserting both that the client
is called with the right arguments and that the response text is formatted as
expected.

The client is injected by forcing ``get_active_client`` down its env-var
fallback (ConfigManager raises) and patching ``CompositeAWXClient`` to return a
fake. Workflow tools call ``client.<method>`` (domain objects); notification
tools call ``client.rest_client.<method>`` (dicts).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from awx_mcp_server.domain import AWXClientError, JobStatus, NoActiveEnvironmentError
from awx_mcp_server.http_server import process_mcp_message
from awx_mcp_server.mcp_server import create_mcp_server

# Markers the call_tool error/validation paths emit; their ABSENCE means the
# handler ran its success path.
_ERROR_MARKERS = (
    "AWX error",
    "Authorization error",
    "Could not reach AWX",
    "Blocked by allowlist",
    "Unexpected error in tool",
    "missing required argument",
    "validation error",
    "Unknown tool",
    "Error:",
)


def assert_ok(text: str) -> None:
    assert not any(m in text for m in _ERROR_MARKERS), f"handler errored: {text[:160]}"


class FakeClient:
    """Async-context-manager stand-in for CompositeAWXClient."""

    def __init__(self, methods=None, rest=None):
        for name, fn in (methods or {}).items():
            setattr(self, name, fn)
        self.rest_client = SimpleNamespace(**(rest or {}))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def invoke(monkeypatch):
    """Return an async ``invoke(name, arguments, client) -> response_text``."""
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
    server = create_mcp_server()

    async def _invoke(name, arguments, client):
        monkeypatch.setattr(
            "awx_mcp_server.mcp_server.CompositeAWXClient", lambda *a, **k: client
        )
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        res = await process_mcp_message(server, msg, "test-tenant")
        return res["result"]["content"][0]["text"]

    return _invoke


# --- Workflow tools (client.<method>, domain objects) ---------------------


async def test_workflow_templates_list(invoke):
    tmpl = SimpleNamespace(
        id=12,
        name="Deploy Pipeline",
        description="prod deploy",
        status="successful",
        last_job_run=None,
        next_job_run=None,
    )
    client = FakeClient(
        methods={"list_workflow_job_templates": AsyncMock(return_value=[tmpl])}
    )
    text = await invoke("awx_workflow_templates_list", {}, client)
    assert "Workflow Job Templates (1)" in text
    assert "ID: 12 - Deploy Pipeline" in text
    client.list_workflow_job_templates.assert_awaited_once()


async def test_workflow_template_get(invoke):
    tmpl = SimpleNamespace(
        name="Deploy Pipeline",
        description="d",
        organization=1,
        inventory=2,
        limit=None,
        status="successful",
        survey_enabled=True,
        allow_simultaneous=False,
        last_job_run=None,
        next_job_run=None,
        ask_variables_on_launch=True,
        ask_inventory_on_launch=False,
        ask_limit_on_launch=False,
        ask_tags_on_launch=False,
        ask_skip_tags_on_launch=False,
    )
    client = FakeClient(
        methods={"get_workflow_job_template": AsyncMock(return_value=tmpl)}
    )
    text = await invoke("awx_workflow_template_get", {"template_id": 12}, client)
    assert "Workflow Job Template 12" in text
    assert "Name: Deploy Pipeline" in text
    client.get_workflow_job_template.assert_awaited_once_with(12)


async def test_workflow_job_launch(invoke):
    tmpl = SimpleNamespace(name="Deploy Pipeline")
    wf_job = SimpleNamespace(
        id=340, name="Deploy Pipeline", status=JobStatus.SUCCESSFUL
    )
    client = FakeClient(
        methods={
            "get_workflow_job_template": AsyncMock(return_value=tmpl),
            "launch_workflow_job": AsyncMock(return_value=wf_job),
        }
    )
    text = await invoke(
        "awx_workflow_job_launch",
        {"template_id": 12, "extra_vars": {"env": "prod"}},
        client,
    )
    assert "launched successfully" in text
    assert "Workflow Job ID: 340" in text
    client.launch_workflow_job.assert_awaited_once()
    kwargs = client.launch_workflow_job.await_args.kwargs
    assert kwargs["template_id"] == 12
    assert kwargs["extra_vars"] == {"env": "prod"}


# --- Notification tools (client.rest_client.<method>, dicts) --------------


async def test_notification_templates_list(invoke):
    rest = {
        "list_notification_templates": AsyncMock(
            return_value=[{"id": 4, "name": "slack-ops", "notification_type": "slack"}]
        )
    }
    client = FakeClient(rest=rest)
    text = await invoke("awx_notification_templates_list", {}, client)
    assert "Notification Templates (1)" in text
    assert "ID: 4 - slack-ops" in text
    assert "Type: slack" in text


async def test_notification_template_create(invoke):
    created = {"id": 7, "name": "email-oncall", "notification_type": "email"}
    rest = {"create_notification_template": AsyncMock(return_value=created)}
    client = FakeClient(rest=rest)
    text = await invoke(
        "awx_notification_template_create",
        {"name": "email-oncall", "organization": 1, "notification_type": "email"},
        client,
    )
    assert "created successfully" in text
    assert "ID: 7" in text
    client.rest_client.create_notification_template.assert_awaited_once()
    kwargs = client.rest_client.create_notification_template.await_args.kwargs
    assert kwargs["name"] == "email-oncall"
    assert kwargs["notification_type"] == "email"


async def test_job_template_notification_associate(invoke):
    rest = {"associate_job_template_notification": AsyncMock(return_value=None)}
    client = FakeClient(rest=rest)
    text = await invoke(
        "awx_job_template_notification_associate",
        {"template_id": 1, "notification_template_id": 4, "event": "error"},
        client,
    )
    assert "associated with job template 1" in text
    assert "'error'" in text
    client.rest_client.associate_job_template_notification.assert_awaited_once_with(
        1, 4, "error"
    )


async def test_job_delete_uses_rest_client(invoke):
    """Regression: awx_job_delete must call client.rest_client.delete_job
    (CompositeAWXClient has no delete_job — was a runtime AttributeError)."""
    rest = {"delete_job": AsyncMock(return_value=None)}
    client = FakeClient(rest=rest)
    text = await invoke("awx_job_delete", {"job_id": 99}, client)
    assert "deleted successfully" in text
    client.rest_client.delete_job.assert_awaited_once_with(99)


# --- Workflow jobs/templates (more of connor-griffin5's tools) ------------


async def test_workflow_job_get(invoke):
    client = FakeClient(
        methods={"get_workflow_job": AsyncMock(return_value=MagicMock())}
    )
    assert_ok(await invoke("awx_workflow_job_get", {"job_id": 5}, client))
    client.get_workflow_job.assert_awaited_once_with(5)


async def test_workflow_jobs_list(invoke):
    client = FakeClient(
        methods={"list_workflow_jobs": AsyncMock(return_value=[MagicMock()])}
    )
    assert_ok(await invoke("awx_workflow_jobs_list", {}, client))


async def test_workflow_job_cancel(invoke):
    client = FakeClient(methods={"cancel_workflow_job": AsyncMock(return_value=None)})
    assert_ok(await invoke("awx_workflow_job_cancel", {"job_id": 5}, client))
    client.cancel_workflow_job.assert_awaited_once_with(5)


async def test_workflow_job_nodes(invoke):
    client = FakeClient(
        methods={"get_workflow_job_nodes": AsyncMock(return_value=[MagicMock()])}
    )
    assert_ok(await invoke("awx_workflow_job_nodes", {"job_id": 5}, client))


async def test_workflow_job_delete(invoke):
    client = FakeClient(rest={"delete_workflow_job": AsyncMock(return_value=None)})
    assert_ok(await invoke("awx_workflow_job_delete", {"job_id": 5}, client))
    client.rest_client.delete_workflow_job.assert_awaited_once_with(5)


async def test_workflow_job_relaunch(invoke):
    client = FakeClient(
        rest={"relaunch_workflow_job": AsyncMock(return_value=MagicMock())}
    )
    assert_ok(await invoke("awx_workflow_job_relaunch", {"job_id": 5}, client))


async def test_workflow_template_nodes(invoke):
    client = FakeClient(
        rest={"get_workflow_job_template_nodes": AsyncMock(return_value=[])}
    )
    assert_ok(await invoke("awx_workflow_template_nodes", {"template_id": 12}, client))


async def test_workflow_template_survey_none(invoke):
    # Empty survey -> the "no survey configured" success path.
    client = FakeClient(
        rest={"get_workflow_job_template_survey": AsyncMock(return_value={})}
    )
    assert_ok(await invoke("awx_workflow_template_survey", {"template_id": 12}, client))


async def test_workflow_template_schedules(invoke):
    client = FakeClient(
        rest={"list_workflow_job_template_schedules": AsyncMock(return_value=[])}
    )
    assert_ok(
        await invoke("awx_workflow_template_schedules", {"template_id": 12}, client)
    )


async def test_workflow_template_launch_config(invoke):
    client = FakeClient(
        rest={"get_workflow_job_template_launch_config": AsyncMock(return_value={})}
    )
    assert_ok(
        await invoke("awx_workflow_template_launch_config", {"template_id": 12}, client)
    )


# --- More notification tools ----------------------------------------------


async def test_notification_template_get(invoke):
    client = FakeClient(
        rest={
            "get_notification_template": AsyncMock(
                return_value={"id": 4, "name": "n", "notification_type": "slack"}
            )
        }
    )
    assert_ok(await invoke("awx_notification_template_get", {"template_id": 4}, client))


async def test_notification_template_update(invoke):
    client = FakeClient(
        rest={
            "update_notification_template": AsyncMock(
                return_value={"id": 4, "name": "n", "notification_type": "slack"}
            )
        }
    )
    assert_ok(
        await invoke(
            "awx_notification_template_update", {"template_id": 4, "name": "n2"}, client
        )
    )


async def test_notification_template_delete(invoke):
    client = FakeClient(
        rest={"delete_notification_template": AsyncMock(return_value=None)}
    )
    assert_ok(
        await invoke("awx_notification_template_delete", {"template_id": 4}, client)
    )
    client.rest_client.delete_notification_template.assert_awaited_once_with(4)


async def test_notification_template_test(invoke):
    client = FakeClient(
        rest={
            "test_notification_template": AsyncMock(
                return_value={"id": 1, "status": "pending"}
            )
        }
    )
    assert_ok(
        await invoke("awx_notification_template_test", {"template_id": 4}, client)
    )


async def test_notifications_list(invoke):
    client = FakeClient(
        rest={
            "list_notifications": AsyncMock(
                return_value=[
                    {"id": 1, "status": "successful", "notification_type": "slack"}
                ]
            )
        }
    )
    assert_ok(await invoke("awx_notifications_list", {}, client))


async def test_job_template_notifications_list(invoke):
    client = FakeClient(
        rest={
            "list_job_template_notification_templates": AsyncMock(
                return_value=[{"id": 4, "name": "n", "notification_type": "slack"}]
            )
        }
    )
    assert_ok(
        await invoke("awx_job_template_notifications_list", {"template_id": 1}, client)
    )


async def test_job_template_notification_disassociate(invoke):
    client = FakeClient(
        rest={"disassociate_job_template_notification": AsyncMock(return_value=None)}
    )
    assert_ok(
        await invoke(
            "awx_job_template_notification_disassociate",
            {"template_id": 1, "notification_template_id": 4, "event": "error"},
            client,
        )
    )


async def test_workflow_template_notifications_list(invoke):
    client = FakeClient(
        rest={
            "list_workflow_template_notification_templates": AsyncMock(
                return_value=[{"id": 4, "name": "n", "notification_type": "slack"}]
            )
        }
    )
    assert_ok(
        await invoke(
            "awx_workflow_template_notifications_list", {"template_id": 12}, client
        )
    )


async def test_workflow_template_notification_associate(invoke):
    client = FakeClient(
        rest={"associate_workflow_template_notification": AsyncMock(return_value=None)}
    )
    assert_ok(
        await invoke(
            "awx_workflow_template_notification_associate",
            {"template_id": 12, "notification_template_id": 4, "event": "success"},
            client,
        )
    )


async def test_workflow_template_notification_disassociate(invoke):
    client = FakeClient(
        rest={
            "disassociate_workflow_template_notification": AsyncMock(return_value=None)
        }
    )
    assert_ok(
        await invoke(
            "awx_workflow_template_notification_disassociate",
            {"template_id": 12, "notification_template_id": 4, "event": "success"},
            client,
        )
    )


# --- Core read/launch tools -----------------------------------------------


async def test_templates_list(invoke):
    client = FakeClient(
        methods={"list_job_templates": AsyncMock(return_value=[MagicMock()])}
    )
    assert_ok(await invoke("awx_templates_list", {}, client))


async def test_job_get(invoke):
    client = FakeClient(methods={"get_job": AsyncMock(return_value=MagicMock())})
    assert_ok(await invoke("awx_job_get", {"job_id": 7}, client))
    client.get_job.assert_awaited_once_with(7)


async def test_jobs_list(invoke):
    client = FakeClient(methods={"list_jobs": AsyncMock(return_value=[MagicMock()])})
    assert_ok(await invoke("awx_jobs_list", {}, client))


async def test_projects_list(invoke):
    client = FakeClient(
        methods={"list_projects": AsyncMock(return_value=[MagicMock()])}
    )
    assert_ok(await invoke("awx_projects_list", {}, client))


async def test_inventories_list(invoke):
    client = FakeClient(
        methods={"list_inventories": AsyncMock(return_value=[MagicMock()])}
    )
    assert_ok(await invoke("awx_inventories_list", {}, client))


async def test_job_launch(invoke):
    client = FakeClient(
        methods={
            "get_job_template": AsyncMock(return_value=MagicMock()),
            "launch_job": AsyncMock(return_value=MagicMock()),
        }
    )
    assert_ok(await invoke("awx_job_launch", {"template_id": 1}, client))
    client.launch_job.assert_awaited_once()


# --- Drift guard ----------------------------------------------------------


async def test_every_declared_tool_is_dispatchable(invoke):
    """Every tool advertised by list_tools must have a dispatch path (registry
    or fall-through) — i.e. invoking it must never return 'Unknown tool'. This
    guards against schema/handler drift in the (still partly monolithic)
    call_tool. Required args / missing client methods produce other errors,
    which is fine; we only assert the tool is *known*."""
    server = create_mcp_server()
    listing = await process_mcp_message(
        server, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, "t"
    )
    names = [t["name"] for t in listing["result"]["tools"]]
    assert len(names) >= 70  # sanity: the full surface is present

    empty_client = FakeClient()
    for name in names:
        text = await invoke(name, {}, empty_client)
        assert "Unknown tool" not in text, f"{name} is declared but not dispatched"


# --- Error / validation paths --------------------------------------------


async def test_client_error_is_typed(invoke):
    """An AWXClientError from the client surfaces as a typed 'AWX error' message
    (verifies the call_tool exception handling end-to-end)."""
    client = FakeClient(
        methods={
            "list_workflow_job_templates": AsyncMock(
                side_effect=AWXClientError("boom from AWX")
            )
        }
    )
    text = await invoke("awx_workflow_templates_list", {}, client)
    assert "AWX error" in text
    assert "boom from AWX" in text


async def test_missing_required_argument(invoke):
    """A missing required argument is rejected by inputSchema validation with a
    clear message naming the field (not a raw KeyError/traceback)."""
    client = FakeClient(
        methods={"get_workflow_job_template": AsyncMock(return_value=None)}
    )
    text = await invoke("awx_workflow_template_get", {}, client)  # no template_id
    assert "validation error" in text.lower()
    assert "template_id" in text
    # The client method must never be reached when a required arg is missing.
    client.get_workflow_job_template.assert_not_awaited()
