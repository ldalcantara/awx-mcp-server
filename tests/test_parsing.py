"""Tests for failure analysis."""

from awx_mcp_server.domain import JobEvent, FailureCategory
from awx_mcp_server.utils import analyze_job_failure


def test_analyze_auth_failure():
    """Test authentication failure detection."""
    events = [
        JobEvent(
            id=1,
            event="runner_on_failed",
            event_level=3,
            failed=True,
            changed=False,
            task="Gather Facts",
            host="web01",
            stdout="",
            stderr="Permission denied (publickey,password)",
            event_data={"res": {"stderr": "Permission denied (publickey,password)"}},
        )
    ]

    analysis = analyze_job_failure(123, events, "")

    assert analysis.category == FailureCategory.AUTH_FAILURE
    assert analysis.host == "web01"
    assert len(analysis.suggested_fixes) > 0
    assert any("SSH" in fix or "credential" in fix for fix in analysis.suggested_fixes)


def test_analyze_missing_variable():
    """Test missing variable detection."""
    events = [
        JobEvent(
            id=1,
            event="runner_on_failed",
            event_level=3,
            failed=True,
            changed=False,
            task="Deploy application",
            host="web01",
            stdout="",
            stderr="",
            event_data={
                "res": {
                    "msg": "The task includes an option with an undefined variable. "
                    "The error was: 'app_version' is undefined"
                }
            },
        )
    ]

    analysis = analyze_job_failure(123, events, "")

    assert analysis.category == FailureCategory.MISSING_VARIABLE
    assert len(analysis.suggested_fixes) > 0
    assert any("variable" in fix.lower() for fix in analysis.suggested_fixes)


def test_analyze_syntax_error():
    """Test syntax error detection."""
    events = [
        JobEvent(
            id=1,
            event="runner_on_failed",
            event_level=3,
            failed=True,
            changed=False,
            task="Parse config",
            host="web01",
            stdout="",
            stderr="Syntax Error while loading YAML",
            event_data={"res": {"stderr": "Syntax Error while loading YAML"}},
        )
    ]

    analysis = analyze_job_failure(123, events, "")

    assert analysis.category == FailureCategory.SYNTAX_ERROR
    assert len(analysis.suggested_fixes) > 0
    assert any(
        "syntax" in fix.lower() or "yaml" in fix.lower()
        for fix in analysis.suggested_fixes
    )


def test_analyze_connection_timeout():
    """Test connection timeout detection."""
    events = [
        JobEvent(
            id=1,
            event="runner_on_unreachable",
            event_level=3,
            failed=True,
            changed=False,
            task="Setup",
            host="web01",
            stdout="",
            stderr="Connection timed out",
            event_data={"res": {"msg": "Connection timed out"}},
        )
    ]

    analysis = analyze_job_failure(123, events, "")

    assert analysis.category == FailureCategory.CONNECTION_TIMEOUT
    assert len(analysis.suggested_fixes) > 0
    assert any(
        "timeout" in fix.lower() or "network" in fix.lower()
        for fix in analysis.suggested_fixes
    )


def test_analyze_no_failed_events():
    """Test analysis with no failed events."""
    events = [
        JobEvent(
            id=1,
            event="runner_on_ok",
            event_level=3,
            failed=False,
            changed=True,
            task="Deploy app",
            host="web01",
        )
    ]

    analysis = analyze_job_failure(123, events, "")

    assert analysis.category == FailureCategory.UNKNOWN
    assert len(analysis.suggested_fixes) > 0


def test_redact_sensitive_masks_secret_keys():
    """Keys carrying credentials must be masked before logging."""
    from awx_mcp_server.utils import redact_sensitive

    args = {
        "template_id": 7,
        "limit": "webservers",
        "extra_vars": {"db_password": "hunter2"},
        "inputs": {"password": "hunter2"},
        "awx_token": "abc123",
    }
    red = redact_sensitive(args)
    assert red["template_id"] == 7
    assert red["limit"] == "webservers"
    assert red["extra_vars"] == "[REDACTED]"
    assert red["inputs"] == "[REDACTED]"
    assert red["awx_token"] == "[REDACTED]"
    # Original is untouched (it is still needed by the tool handler).
    assert args["extra_vars"] == {"db_password": "hunter2"}


def test_redact_sensitive_walks_containers_and_passes_scalars():
    from awx_mcp_server.utils import redact_sensitive

    assert redact_sensitive([{"token": "t", "name": "n"}]) == [
        {"token": "[REDACTED]", "name": "n"}
    ]
    assert redact_sensitive("plain") == "plain"
    assert redact_sensitive(None) is None
