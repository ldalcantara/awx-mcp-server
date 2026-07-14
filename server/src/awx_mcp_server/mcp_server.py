"""MCP Server implementation for AWX integration."""

import asyncio
import hashlib
import os
from collections import OrderedDict
from typing import Any, Optional
from uuid import uuid4

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

from awx_mcp_server.clients import RestAWXClient
from awx_mcp_server.domain import (
    AllowlistViolationError,
    AWXAuthenticationError,
    AWXClientError,
    AWXConnectionError,
    AWXMCPError,
    AWXPermissionError,
    CredentialType,
    EnvironmentConfig,
    NoActiveEnvironmentError,
)
from awx_mcp_server.storage import ConfigManager, CredentialStore
from awx_mcp_server.tools import TOOL_MODULES
from awx_mcp_server.tools.context import ToolContext
from awx_mcp_server.utils import (
    configure_logging,
    get_logger,
    redact_sensitive,
)

# Initialize logging
configure_logging()
logger = get_logger(__name__)


def create_mcp_server(tenant_id: Optional[str] = None) -> Server:
    """
    Create MCP server instance.

    Args:
        tenant_id: Tenant ID for multi-tenant isolation (optional)

    Returns:
        Configured MCP Server instance
    """
    # Create MCP server
    mcp_server = Server("awx-mcp-server")

    # Initialize storage with tenant context
    config_manager = ConfigManager(tenant_id=tenant_id)
    credential_store = CredentialStore(tenant_id=tenant_id)

    # One client per resolved (URL, credentials), so repeated tool calls reuse
    # a warm HTTP connection pool instead of paying a fresh TCP+TLS handshake
    # per call. Cached clients are marked ``persistent`` so the per-handler
    # ``async with client`` blocks don't close them.
    client_cache: OrderedDict[tuple, RestAWXClient] = OrderedDict()
    client_cache_max = 8
    # Hold references to eviction-close tasks: a bare create_task() result can
    # be garbage-collected before it runs and its exception is never observed.
    close_tasks: set[asyncio.Task] = set()

    def _close_task_done(task: asyncio.Task) -> None:
        close_tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.warning(f"Error closing evicted AWX client: {task.exception()!r}")

    def cached_client(
        env: EnvironmentConfig,
        username: Optional[str],
        secret: str,
        is_token: bool,
    ) -> RestAWXClient:
        # env_id is excluded from the key: the env-var fallback mints a fresh
        # uuid on every call, which would defeat the cache.
        key = (
            str(env.base_url),
            username or "",
            hashlib.sha256((secret or "").encode()).hexdigest(),
            is_token,
            env.verify_ssl,
        )
        client = client_cache.get(key)
        if client is None:
            client = RestAWXClient(env, username, secret, is_token)
            client.persistent = True
            while len(client_cache) >= client_cache_max:
                _, evicted = client_cache.popitem(last=False)
                try:
                    task = asyncio.get_running_loop().create_task(evicted.aclose())
                    close_tasks.add(task)
                    task.add_done_callback(_close_task_done)
                except RuntimeError:
                    # No running loop (sync caller): dropping the reference
                    # lets the pool's idle sockets be reclaimed by GC.
                    pass
            client_cache[key] = client
        else:
            client_cache.move_to_end(key)
        return client

    def get_active_client() -> tuple[EnvironmentConfig, RestAWXClient]:
        """Get client for active environment, falling back to environment variables if no config exists."""
        try:
            # Try to get stored environment
            env = config_manager.get_active()

            # Determine credential type
            try:
                username, secret = credential_store.get_credential(
                    env.env_id, CredentialType.PASSWORD
                )
                is_token = False
            except Exception:
                username, secret = credential_store.get_credential(
                    env.env_id, CredentialType.TOKEN
                )
                is_token = True

            return env, cached_client(env, username, secret, is_token)

        except Exception as e:
            # Fall back to environment variables. NoActiveEnvironmentError is
            # the expected fresh-install / env-var-only case; anything else is
            # a real storage or keyring fault, so surface it at WARNING with
            # its class instead of hiding it as routine.
            if isinstance(e, NoActiveEnvironmentError):
                logger.info(
                    "No stored environment configured; using environment variables"
                )
            else:
                logger.warning(
                    f"Stored-environment lookup failed ({type(e).__name__}: {e}); "
                    "falling back to environment variables"
                )

            # Per-request overrides (HTTP X-AWX-* headers) arrive via a
            # task-local ContextVar, not process-global os.environ, so
            # concurrent requests can't read each other's credentials.
            from awx_mcp_server.request_context import get_awx_override

            override = get_awx_override()

            def _cfg(key: str, default: Optional[str] = None) -> Optional[str]:
                return override.get(key) or os.getenv(key, default)

            awx_base_url = _cfg("AWX_BASE_URL")
            awx_token = _cfg("AWX_TOKEN")
            awx_username = _cfg("AWX_USERNAME")
            awx_password = _cfg("AWX_PASSWORD")
            awx_platform = (_cfg("AWX_PLATFORM", "awx") or "awx").lower()
            awx_verify_ssl = (
                _cfg("AWX_VERIFY_SSL", "true") or "true"
            ).lower() == "true"

            # Validate platform type
            from awx_mcp_server.domain import PlatformType

            try:
                platform_type = PlatformType(awx_platform)
            except ValueError:
                logger.warning(
                    f"Invalid AWX_PLATFORM value '{awx_platform}', defaulting to 'awx'"
                )
                platform_type = PlatformType.AWX

            # Debug logging
            logger.info(
                f"Environment variables: AWX_BASE_URL={awx_base_url}, AWX_PLATFORM={platform_type.value}, AWX_TOKEN={'*' * 10 if awx_token else None}, AWX_USERNAME={awx_username}, AWX_VERIFY_SSL={awx_verify_ssl}"
            )

            if not awx_base_url:
                raise NoActiveEnvironmentError(
                    "No active environment configured and AWX_BASE_URL environment variable not set"
                )

            # Create temporary environment from env vars
            temp_env = EnvironmentConfig(
                env_id=uuid4(),
                name="default",
                base_url=awx_base_url,
                platform_type=platform_type,
                verify_ssl=awx_verify_ssl,
                is_default=True,
                allowed_job_templates=[],
                allowed_inventories=[],
            )

            # Determine auth method
            if awx_token:
                logger.info("Using AWX_TOKEN from environment variables")
                client = cached_client(temp_env, "", awx_token, is_token=True)
            elif awx_username and awx_password:
                logger.info(
                    "Using AWX_USERNAME/AWX_PASSWORD from environment variables"
                )
                client = cached_client(
                    temp_env, awx_username, awx_password, is_token=False
                )
            else:
                raise NoActiveEnvironmentError(
                    "No active environment configured and neither AWX_TOKEN nor AWX_USERNAME/AWX_PASSWORD set"
                )

            return temp_env, client

    def check_allowlist(
        env: EnvironmentConfig, template_id: int, template_name: str
    ) -> None:
        """Check if template is in allowlist."""
        if env.allowed_job_templates and template_name not in env.allowed_job_templates:
            raise AllowlistViolationError(
                f"Template '{template_name}' not in allowlist for environment '{env.name}'"
            )

    def make_client(
        env: EnvironmentConfig,
        username: Optional[str],
        secret: str,
        is_token: bool = False,
    ) -> RestAWXClient:
        """Build a client in THIS module's namespace (tests monkeypatch
        ``awx_mcp_server.mcp_server.RestAWXClient``)."""
        return RestAWXClient(env, username, secret, is_token)

    ctx = ToolContext(
        config_manager=config_manager,
        credential_store=credential_store,
        get_active_client=get_active_client,
        check_allowlist=check_allowlist,
        make_client=make_client,
    )

    # One dispatch mechanism: every tool lives in a domain module under
    # awx_mcp_server/tools/ and registers its handlers here.
    _HANDLERS: dict[str, Any] = {}
    for _module in TOOL_MODULES:
        _HANDLERS.update(_module.register(ctx))

    @mcp_server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [tool for module in TOOL_MODULES for tool in module.TOOLS]

    @mcp_server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        """Handle tool calls by dispatching to the registered handler."""
        try:
            # Redact credential inputs / extra_vars etc. before logging.
            logger.info("tool_call", tool=name, arguments=redact_sensitive(arguments))
            handler = _HANDLERS.get(name)
            if handler is None:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
            return await handler(arguments)
        except KeyError as e:
            # A required argument was missing from the tool call.
            logger.error("tool_error", tool=name, error=f"missing argument {e}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: missing required argument {e} for tool '{name}'.",
                )
            ]
        except (AWXAuthenticationError, AWXPermissionError) as e:
            logger.error("tool_error", tool=name, error=str(e))
            return [
                TextContent(
                    type="text",
                    text=f"Authorization error from AWX: {e}. "
                    "Check the active environment's credentials and permissions.",
                )
            ]
        except AWXConnectionError as e:
            logger.error("tool_error", tool=name, error=str(e))
            return [
                TextContent(
                    type="text",
                    text=f"Could not reach AWX: {e}. "
                    "Check the environment URL and network connectivity.",
                )
            ]
        except AllowlistViolationError as e:
            logger.error("tool_error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Blocked by allowlist policy: {e}.")]
        except (AWXClientError, AWXMCPError) as e:
            logger.error("tool_error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"AWX error: {e}")]
        except Exception as e:
            # Unexpected/unclassified error: log the full traceback for triage.
            logger.exception("tool_error_unexpected", tool=name)
            return [
                TextContent(type="text", text=f"Unexpected error in tool '{name}': {e}")
            ]

    return mcp_server


async def main() -> None:
    """Run MCP server in stdio mode (for local VSCode integration)."""
    logger.info("starting_stdio_server")

    # Create server without tenant isolation for local use
    mcp_server = create_mcp_server()

    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
