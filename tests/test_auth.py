"""Unit tests for auth.APIKeyManager and TenantContext (no live AWX).

The manager stores keys by sha256 hash (never plaintext) and enforces
active/expiry state on verification — the security-relevant contract.
"""

import hashlib
from datetime import datetime, timedelta

import pytest

from awx_mcp_server.auth import APIKeyManager, TenantContext


@pytest.fixture
def mgr():
    return APIKeyManager()


def test_generate_key_stores_hash_not_plaintext(mgr):
    plaintext, api_key = mgr.generate_key("ci", tenant_id="t1")
    assert plaintext.startswith("awx_mcp_")
    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    assert api_key.key_hash == expected_hash
    # stored keyed by the hash; the plaintext appears nowhere in the store
    assert expected_hash in mgr.keys
    assert plaintext not in mgr.keys
    assert api_key.tenant_id == "t1"


def test_generate_key_sets_expiry_and_permissions(mgr):
    _, with_expiry = mgr.generate_key("a", "t1", expires_days=10)
    assert with_expiry.expires_at is not None
    delta = with_expiry.expires_at - with_expiry.created_at
    assert delta == timedelta(days=10)
    assert with_expiry.permissions == ["read", "write", "execute"]

    _, no_expiry = mgr.generate_key("b", "t1", expires_days=None)
    assert no_expiry.expires_at is None

    _, scoped = mgr.generate_key("c", "t1", permissions=["read"])
    assert scoped.permissions == ["read"]


def test_verify_key_valid_updates_last_used(mgr):
    plaintext, api_key = mgr.generate_key("ci", "t1")
    assert api_key.last_used is None
    verified = mgr.verify_key(plaintext)
    assert verified is api_key
    assert verified.last_used is not None


def test_verify_key_unknown_returns_none(mgr):
    mgr.generate_key("ci", "t1")
    assert mgr.verify_key("awx_mcp_not-a-real-key") is None


def test_verify_key_revoked_returns_none(mgr):
    plaintext, api_key = mgr.generate_key("ci", "t1")
    assert mgr.revoke_key(api_key.key_hash) is True
    assert mgr.verify_key(plaintext) is None


def test_verify_key_expired_returns_none(mgr):
    plaintext, api_key = mgr.generate_key("ci", "t1", expires_days=1)
    api_key.expires_at = datetime.utcnow() - timedelta(seconds=1)
    assert mgr.verify_key(plaintext) is None


def test_revoke_unknown_hash_returns_false(mgr):
    assert mgr.revoke_key("deadbeef") is False


def test_list_keys_filters_by_tenant(mgr):
    mgr.generate_key("a", "t1")
    mgr.generate_key("b", "t1")
    mgr.generate_key("c", "t2")
    assert len(mgr.list_keys()) == 3
    assert {k.tenant_id for k in mgr.list_keys("t1")} == {"t1"}
    assert len(mgr.list_keys("t1")) == 2
    assert mgr.list_keys("nope") == []


def test_tenant_context_set_get_clear():
    try:
        assert TenantContext.get_tenant() is None
        TenantContext.set_tenant("t42")
        assert TenantContext.get_tenant() == "t42"
    finally:
        TenantContext.clear()
    assert TenantContext.get_tenant() is None
