"""Client-robustness regression tests (no live AWX).

Covers extra_vars shape normalization on the REST client's shared base parser.
(The former awxkit/composite CLI-fallback layer was removed; the REST client is
now used directly.)
"""

from awx_mcp_server.clients.base import AWXClient


def test_parse_extra_vars_normalizes_json_string():
    """A JSON-string extra_vars must be normalized to a dict."""
    assert AWXClient._parse_extra_vars('{"env": "prod"}') == {"env": "prod"}


def test_parse_extra_vars_passes_through_dict():
    assert AWXClient._parse_extra_vars({"env": "prod"}) == {"env": "prod"}


def test_parse_extra_vars_empty_and_invalid_are_empty_dict():
    assert AWXClient._parse_extra_vars("") == {}
    assert AWXClient._parse_extra_vars(None) == {}
    assert AWXClient._parse_extra_vars("not-json") == {}
