"""Environment-management tools (stored AWX environments)."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.domain import CredentialType, NoActiveEnvironmentError
from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    # Environment Management
    Tool(
        name="env_list",
        description="List all configured AWX environments",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="env_set_active",
        description="Set the active AWX environment",
        inputSchema={
            "type": "object",
            "properties": {
                "env_name": {
                    "type": "string",
                    "description": "Environment name",
                },
            },
            "required": ["env_name"],
        },
    ),
    Tool(
        name="env_get_active",
        description="Get the currently active AWX environment",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="env_test_connection",
        description="Test connection to an AWX environment",
        inputSchema={
            "type": "object",
            "properties": {
                "env_name": {
                    "type": "string",
                    "description": "Environment name (optional, uses active if not specified)",
                },
            },
        },
    ),
]


async def _h_env_list(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    envs = ctx.config_manager.list_environments()
    active_name = ctx.config_manager.get_active_name()

    result = "Configured AWX Environments:\n\n"
    for env in envs:
        marker = "* " if env.name == active_name else "  "
        result += f"{marker}{env.name}\n"
        result += f"  URL: {env.base_url}\n"
        result += f"  SSL Verify: {env.verify_ssl}\n"
        if env.default_organization:
            result += f"  Default Org: {env.default_organization}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_env_set_active(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    env_name = arguments["env_name"]
    ctx.config_manager.set_active(env_name)
    return [TextContent(type="text", text=f"Active environment set to: {env_name}")]


async def _h_env_get_active(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    try:
        env = ctx.config_manager.get_active()
        return [TextContent(type="text", text=f"Active environment: {env.name}")]
    except NoActiveEnvironmentError:
        return [TextContent(type="text", text="No active environment set")]


async def _h_env_test_connection(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    env_name = arguments.get("env_name")

    if env_name:
        env = ctx.config_manager.get_environment(env_name)
        try:
            username, secret = ctx.credential_store.get_credential(
                env.env_id, CredentialType.PASSWORD
            )
            is_token = False
        except Exception:
            username, secret = ctx.credential_store.get_credential(
                env.env_id, CredentialType.TOKEN
            )
            is_token = True

        client = ctx.make_client(env, username, secret, is_token)
    else:
        env, client = ctx.get_active_client()

    async with client:
        success = await client.test_connection()

    if success:
        return [TextContent(type="text", text=f"✓ Connection successful to {env.name}")]
    else:
        return [TextContent(type="text", text=f"✗ Connection failed to {env.name}")]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "env_list": partial(_h_env_list, ctx),
        "env_set_active": partial(_h_env_set_active, ctx),
        "env_get_active": partial(_h_env_get_active, ctx),
        "env_test_connection": partial(_h_env_test_connection, ctx),
    }
