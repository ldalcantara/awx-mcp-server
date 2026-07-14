"""Inventory, group, and host tools."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    Tool(
        name="awx_inventories_list",
        description="List AWX inventories",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter inventories by name",
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
        name="awx_inventory_create",
        description="Create AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Inventory name"},
                "organization": {
                    "type": "number",
                    "description": "Organization ID",
                },
                "description": {
                    "type": "string",
                    "description": "Inventory description",
                },
                "variables": {
                    "type": "object",
                    "description": "Inventory variables",
                },
            },
            "required": ["name", "organization"],
        },
    ),
    Tool(
        name="awx_inventory_delete",
        description="Delete AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "inventory_id": {
                    "type": "number",
                    "description": "Inventory ID",
                },
            },
            "required": ["inventory_id"],
        },
    ),
    Tool(
        name="awx_inventory_groups_list",
        description="List groups in AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "inventory_id": {
                    "type": "number",
                    "description": "Inventory ID",
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
            "required": ["inventory_id"],
        },
    ),
    Tool(
        name="awx_inventory_group_create",
        description="Create group in AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "inventory_id": {
                    "type": "number",
                    "description": "Inventory ID",
                },
                "name": {"type": "string", "description": "Group name"},
                "description": {
                    "type": "string",
                    "description": "Group description",
                },
                "variables": {
                    "type": "object",
                    "description": "Group variables",
                },
            },
            "required": ["inventory_id", "name"],
        },
    ),
    Tool(
        name="awx_inventory_group_delete",
        description="Delete group from AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "group_id": {"type": "number", "description": "Group ID"},
            },
            "required": ["group_id"],
        },
    ),
    Tool(
        name="awx_inventory_hosts_list",
        description="List hosts in AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "inventory_id": {
                    "type": "number",
                    "description": "Inventory ID",
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
            "required": ["inventory_id"],
        },
    ),
    Tool(
        name="awx_inventory_host_create",
        description="Create host in AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "inventory_id": {
                    "type": "number",
                    "description": "Inventory ID",
                },
                "name": {"type": "string", "description": "Host name"},
                "description": {
                    "type": "string",
                    "description": "Host description",
                },
                "variables": {
                    "type": "object",
                    "description": "Host variables",
                },
            },
            "required": ["inventory_id", "name"],
        },
    ),
    Tool(
        name="awx_inventory_host_delete",
        description="Delete host from AWX inventory",
        inputSchema={
            "type": "object",
            "properties": {
                "host_id": {"type": "number", "description": "Host ID"},
            },
            "required": ["host_id"],
        },
    ),
]


async def _h_awx_inventories_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        inventories = await client.list_inventories(
            name_filter=arguments.get("filter"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Inventories ({len(inventories)}):\n\n"
    for inv in inventories:
        result += f"ID: {inv.id} - {inv.name}\n"
        if inv.description:
            result += f"  Description: {inv.description}\n"
        result += f"  Total Hosts: {inv.total_hosts}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


# Inventories CRUD
async def _h_awx_inventory_create(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        inventory = await client.create_inventory(
            name=arguments["name"],
            organization=arguments["organization"],
            description=arguments.get("description", ""),
            variables=arguments.get("variables"),
        )

    result = "✓ Inventory created successfully\n\n"
    result += f"ID: {inventory.id}\n"
    result += f"Name: {inventory.name}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_inventory_delete(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    inventory_id = arguments["inventory_id"]

    async with client:
        await client.delete_inventory(inventory_id)

    return [
        TextContent(
            type="text",
            text=f"Inventory {inventory_id} deleted successfully",
        )
    ]


# Inventory Groups
async def _h_awx_inventory_groups_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    inventory_id = arguments["inventory_id"]

    async with client:
        groups = await client.list_inventory_groups(
            inventory_id=inventory_id,
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Inventory {inventory_id} Groups ({len(groups)}):\n\n"
    for group in groups:
        result += f"ID: {group['id']} - {group['name']}\n"
        if group.get("description"):
            result += f"  Description: {group['description']}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_inventory_group_create(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    inventory_id = arguments["inventory_id"]

    async with client:
        group = await client.create_inventory_group(
            inventory_id=inventory_id,
            name=arguments["name"],
            description=arguments.get("description", ""),
            variables=arguments.get("variables"),
        )

    result = "✓ Group created successfully\n\n"
    result += f"ID: {group['id']}\n"
    result += f"Name: {group['name']}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_inventory_group_delete(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    group_id = arguments["group_id"]

    async with client:
        await client.delete_inventory_group(group_id)

    return [TextContent(type="text", text=f"Group {group_id} deleted successfully")]


# Inventory Hosts
async def _h_awx_inventory_hosts_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    inventory_id = arguments["inventory_id"]

    async with client:
        hosts = await client.list_inventory_hosts(
            inventory_id=inventory_id,
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Inventory {inventory_id} Hosts ({len(hosts)}):\n\n"
    for host in hosts:
        result += f"ID: {host['id']} - {host['name']}\n"
        if host.get("description"):
            result += f"  Description: {host['description']}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_inventory_host_create(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    inventory_id = arguments["inventory_id"]

    async with client:
        host = await client.create_inventory_host(
            inventory_id=inventory_id,
            name=arguments["name"],
            description=arguments.get("description", ""),
            variables=arguments.get("variables"),
        )

    result = "✓ Host created successfully\n\n"
    result += f"ID: {host['id']}\n"
    result += f"Name: {host['name']}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_inventory_host_delete(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    host_id = arguments["host_id"]

    async with client:
        await client.delete_inventory_host(host_id)

    return [TextContent(type="text", text=f"Host {host_id} deleted successfully")]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "awx_inventories_list": partial(_h_awx_inventories_list, ctx),
        "awx_inventory_create": partial(_h_awx_inventory_create, ctx),
        "awx_inventory_delete": partial(_h_awx_inventory_delete, ctx),
        "awx_inventory_groups_list": partial(_h_awx_inventory_groups_list, ctx),
        "awx_inventory_group_create": partial(_h_awx_inventory_group_create, ctx),
        "awx_inventory_group_delete": partial(_h_awx_inventory_group_delete, ctx),
        "awx_inventory_hosts_list": partial(_h_awx_inventory_hosts_list, ctx),
        "awx_inventory_host_create": partial(_h_awx_inventory_host_create, ctx),
        "awx_inventory_host_delete": partial(_h_awx_inventory_host_delete, ctx),
    }
