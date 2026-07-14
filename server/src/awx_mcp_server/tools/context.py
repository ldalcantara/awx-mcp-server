"""Shared context handed to every tool module.

Bundles the tenant-scoped storage plus the client helpers that used to be
closures inside ``create_mcp_server()``, so handlers can live in per-domain
modules instead of one god-file. ``make_client`` is provided by
``mcp_server`` so client construction stays in that module's namespace
(tests monkeypatch ``awx_mcp_server.mcp_server.RestAWXClient``).
"""

from dataclasses import dataclass
from typing import Callable

from awx_mcp_server.clients import RestAWXClient
from awx_mcp_server.domain import EnvironmentConfig
from awx_mcp_server.storage import ConfigManager, CredentialStore


@dataclass(frozen=True)
class ToolContext:
    """Server-scoped dependencies for tool handlers."""

    config_manager: ConfigManager
    credential_store: CredentialStore
    get_active_client: Callable[[], tuple[EnvironmentConfig, RestAWXClient]]
    check_allowlist: Callable[..., None]
    make_client: Callable[..., RestAWXClient]
