"""Unit tests for monitoring (RequestTimer error labelling)."""

from awx_mcp_server import monitoring as m


def test_request_timer_records_exception_type():
    """RequestTimer must report the real exception type to record_request
    (the ERROR_COUNT label used to be hardcoded to 'unknown')."""
    captured = {}
    original = m.MonitoringService.record_request

    def spy(self, *args, **kwargs):
        captured.update(kwargs)
        return original(self, *args, **kwargs)

    m.MonitoringService.record_request = spy
    try:
        try:
            with m.RequestTimer(tenant_id="t", endpoint="/mcp", method="POST"):
                raise ValueError("boom")
        except ValueError:
            pass
    finally:
        m.MonitoringService.record_request = original

    assert captured.get("error_type") == "ValueError"
    assert captured.get("error") == "boom"
    assert captured.get("status_code") == 500


def test_request_timer_no_error_on_success():
    captured = {}
    original = m.MonitoringService.record_request

    def spy(self, *args, **kwargs):
        captured.update(kwargs)
        return original(self, *args, **kwargs)

    m.MonitoringService.record_request = spy
    try:
        with m.RequestTimer(tenant_id="t", endpoint="/health", method="GET"):
            pass
    finally:
        m.MonitoringService.record_request = original

    assert captured.get("error") is None
    assert captured.get("error_type") is None
    assert captured.get("status_code") == 200
