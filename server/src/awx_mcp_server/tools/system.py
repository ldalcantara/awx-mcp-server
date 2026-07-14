"""System info, organization, and credential tools."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    # System Info
    Tool(
        name="awx_system_info",
        description="Get AWX system information (config, dashboard, settings)",
        inputSchema={
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "description": "Type of info: config, dashboard, settings, me",
                    "enum": ["config", "dashboard", "settings", "me"],
                },
            },
            "required": ["info_type"],
        },
    ),
    # Organizations
    Tool(
        name="awx_organizations_list",
        description="List AWX organizations",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter organizations by name",
                },
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                },
                "page_size": {
                    "type": "number",
                    "description": "Page size (default: 25)",
                },
            },
        },
    ),
    Tool(
        name="awx_organization_get",
        description="Get AWX organization by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "org_id": {"type": "number", "description": "Organization ID"},
            },
            "required": ["org_id"],
        },
    ),
    # Credentials
    Tool(
        name="awx_credentials_list",
        description="List AWX credentials",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter credentials by name",
                },
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                },
                "page_size": {
                    "type": "number",
                    "description": "Page size (default: 25)",
                },
            },
        },
    ),
    Tool(
        name="awx_credential_types_list",
        description="List AWX credential types",
        inputSchema={
            "type": "object",
            "properties": {
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                },
                "page_size": {
                    "type": "number",
                    "description": "Page size (default: 25)",
                },
            },
        },
    ),
    Tool(
        name="awx_credential_create",
        description="Create AWX credential",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Credential name"},
                "credential_type": {
                    "type": "number",
                    "description": "Credential type ID",
                },
                "organization": {
                    "type": "number",
                    "description": "Organization ID",
                },
                "inputs": {
                    "type": "object",
                    "description": "Credential inputs (e.g., username, password)",
                },
                "description": {
                    "type": "string",
                    "description": "Credential description",
                },
            },
            "required": ["name", "credential_type", "organization", "inputs"],
        },
    ),
    Tool(
        name="awx_credential_delete",
        description="Delete AWX credential",
        inputSchema={
            "type": "object",
            "properties": {
                "credential_id": {
                    "type": "number",
                    "description": "Credential ID",
                },
            },
            "required": ["credential_id"],
        },
    ),
]


# System Info
async def _h_awx_system_info(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    env, client = ctx.get_active_client()
    info_type = arguments["info_type"]

    async with client:
        if info_type == "config":
            data = await client.get_config()
            result = "AWX System Configuration:\n\n"
            for key, value in data.items():
                result += f"{key}: {value}\n"
        elif info_type == "dashboard":
            data = await client.get_dashboard()
            result = "AWX Dashboard:\n\n"
            for key, value in data.items():
                result += f"{key}: {value}\n"
        elif info_type == "settings":
            data = await client.get_settings()
            result = "AWX Settings:\n\n"
            for key, value in data.items():
                result += f"{key}: {value}\n"
        elif info_type == "me":
            data = await client.get_me()
            result = "Current User Info:\n\n"
            result += f"ID: {data.get('id')}\n"
            result += f"Username: {data.get('username')}\n"
            result += f"Email: {data.get('email', 'N/A')}\n"
            result += f"First Name: {data.get('first_name', 'N/A')}\n"
            result += f"Last Name: {data.get('last_name', 'N/A')}\n"
            result += f"Is Superuser: {data.get('is_superuser', False)}\n"

    return [TextContent(type="text", text=result)]


# Organizations
async def _h_awx_organizations_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        orgs = await client.list_organizations(
            name_filter=arguments.get("filter"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Organizations ({len(orgs)}):\n\n"
    for org in orgs:
        result += f"ID: {org['id']} - {org['name']}\n"
        if org.get("description"):
            result += f"  Description: {org['description']}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_organization_get(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    org_id = arguments["org_id"]

    async with client:
        org = await client.get_organization(org_id)

    result = f"Organization {org_id}:\n\n"
    result += f"Name: {org['name']}\n"
    if org.get("description"):
        result += f"Description: {org['description']}\n"
    result += f"ID: {org['id']}\n"

    return [TextContent(type="text", text=result)]


# Credentials
async def _h_awx_credentials_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        creds = await client.list_credentials(
            name_filter=arguments.get("filter"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Credentials ({len(creds)}):\n\n"
    for cred in creds:
        result += f"ID: {cred['id']} - {cred['name']}\n"
        if cred.get("description"):
            result += f"  Description: {cred['description']}\n"
        result += f"  Type: {cred.get('credential_type')}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_credential_types_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        types = await client.list_credential_types(
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Credential Types ({len(types)}):\n\n"
    for ctype in types:
        result += f"ID: {ctype['id']} - {ctype['name']}\n"
        if ctype.get("description"):
            result += f"  Description: {ctype['description']}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_credential_create(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        cred = await client.create_credential(
            name=arguments["name"],
            credential_type=arguments["credential_type"],
            organization=arguments["organization"],
            inputs=arguments["inputs"],
            description=arguments.get("description", ""),
        )

    result = "✓ Credential created successfully\n\n"
    result += f"ID: {cred['id']}\n"
    result += f"Name: {cred['name']}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_credential_delete(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    cred_id = arguments["credential_id"]

    async with client:
        await client.delete_credential(cred_id)

    return [TextContent(type="text", text=f"Credential {cred_id} deleted successfully")]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "awx_system_info": partial(_h_awx_system_info, ctx),
        "awx_organizations_list": partial(_h_awx_organizations_list, ctx),
        "awx_organization_get": partial(_h_awx_organization_get, ctx),
        "awx_credentials_list": partial(_h_awx_credentials_list, ctx),
        "awx_credential_types_list": partial(_h_awx_credential_types_list, ctx),
        "awx_credential_create": partial(_h_awx_credential_create, ctx),
        "awx_credential_delete": partial(_h_awx_credential_delete, ctx),
    }
