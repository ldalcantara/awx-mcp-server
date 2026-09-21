"""AWX project tools."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    Tool(
        name="awx_projects_list",
        description="List AWX projects",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter projects by name",
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
        name="awx_project_create",
        description="Create AWX project",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "organization": {
                    "type": "number",
                    "description": "Organization ID",
                },
                "scm_type": {
                    "type": "string",
                    "description": "SCM type (git, svn, etc.)",
                    "enum": ["git", "svn", "insights", "archive", ""],
                },
                "scm_url": {
                    "type": "string",
                    "description": "SCM repository URL",
                },
                "scm_branch": {
                    "type": "string",
                    "description": "SCM branch/tag/commit",
                },
                "description": {
                    "type": "string",
                    "description": "Project description",
                },
            },
            "required": ["name", "organization"],
        },
    ),
    Tool(
        name="awx_project_delete",
        description="Delete AWX project",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "number", "description": "Project ID"},
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="awx_project_update",
        description="Update AWX project from SCM",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "number", "description": "Project ID"},
                "wait": {
                    "type": "boolean",
                    "description": "Wait for update to complete",
                },
            },
            "required": ["project_id"],
        },
    ),
]


async def _h_awx_projects_list(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    async with client:
        projects = await client.list_projects(
            name_filter=arguments.get("filter"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Projects ({len(projects)}):\n\n"
    for proj in projects:
        result += f"ID: {proj.id} - {proj.name}\n"
        if proj.description:
            result += f"  Description: {proj.description}\n"
        if proj.scm_url:
            result += f"  SCM: {proj.scm_type} - {proj.scm_url}\n"
        if proj.scm_branch:
            result += f"  Branch: {proj.scm_branch}\n"
        result += f"  Status: {proj.status}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


# Projects CRUD
async def _h_awx_project_create(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    async with client:
        project = await client.create_project(
            name=arguments["name"],
            organization=arguments["organization"],
            scm_type=arguments.get("scm_type", "git"),
            scm_url=arguments.get("scm_url"),
            scm_branch=arguments.get("scm_branch", "main"),
            description=arguments.get("description", ""),
        )

    result = "✓ Project created successfully\n\n"
    result += f"ID: {project.id}\n"
    result += f"Name: {project.name}\n"
    if project.scm_url:
        result += f"SCM: {project.scm_url}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_project_delete(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    project_id = arguments["project_id"]

    async with client:
        await client.delete_project(project_id)

    return [TextContent(type="text", text=f"Project {project_id} deleted successfully")]


async def _h_awx_project_update(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    project_id = arguments["project_id"]
    wait = arguments.get("wait", True)

    async with client:
        result_data = await client.update_project(project_id, wait)

    return [
        TextContent(
            type="text",
            text=f"Project {project_id} update initiated. Result: {result_data}",
        )
    ]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "awx_projects_list": partial(_h_awx_projects_list, ctx),
        "awx_project_create": partial(_h_awx_project_create, ctx),
        "awx_project_delete": partial(_h_awx_project_delete, ctx),
        "awx_project_update": partial(_h_awx_project_update, ctx),
    }
