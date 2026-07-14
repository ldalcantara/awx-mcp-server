"""Job-template tools."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    # Discovery
    Tool(
        name="awx_templates_list",
        description="List AWX job templates (NOT for recent jobs or job history). Templates are playbook definitions, configurations, settings. This shows available templates to run, not execution history or recent activity. For recent jobs/runs/executions, use awx_jobs_list instead.",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter templates by name",
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
        name="awx_template_create",
        description="Create AWX job template",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Template name"},
                "inventory": {"type": "number", "description": "Inventory ID"},
                "project": {"type": "number", "description": "Project ID"},
                "playbook": {
                    "type": "string",
                    "description": "Playbook filename",
                },
                "job_type": {
                    "type": "string",
                    "description": "Job type (run or check)",
                    "enum": ["run", "check"],
                },
                "description": {
                    "type": "string",
                    "description": "Template description",
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables",
                },
                "limit": {
                    "type": "string",
                    "description": "Host limit pattern",
                },
            },
            "required": ["name", "inventory", "project", "playbook"],
        },
    ),
    Tool(
        name="awx_template_delete",
        description="Delete AWX job template",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {"type": "number", "description": "Template ID"},
            },
            "required": ["template_id"],
        },
    ),
]


async def _h_awx_templates_list(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        templates = await client.list_job_templates(
            name_filter=arguments.get("filter"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Job Templates ({len(templates)}):\n\n"
    for tmpl in templates:
        result += f"ID: {tmpl.id} - {tmpl.name}\n"
        if tmpl.description:
            result += f"  Description: {tmpl.description}\n"
        result += f"  Playbook: {tmpl.playbook}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


# Templates CRUD
async def _h_awx_template_create(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        template = await client.create_job_template(
            name=arguments["name"],
            inventory=arguments["inventory"],
            project=arguments["project"],
            playbook=arguments["playbook"],
            job_type=arguments.get("job_type", "run"),
            description=arguments.get("description", ""),
            extra_vars=arguments.get("extra_vars"),
            limit=arguments.get("limit"),
        )

    result = "✓ Job template created successfully\n\n"
    result += f"ID: {template.id}\n"
    result += f"Name: {template.name}\n"
    result += f"Playbook: {template.playbook}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_template_delete(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        await client.delete_job_template(template_id)

    return [
        TextContent(
            type="text",
            text=f"Job template {template_id} deleted successfully",
        )
    ]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "awx_templates_list": partial(_h_awx_templates_list, ctx),
        "awx_template_create": partial(_h_awx_template_create, ctx),
        "awx_template_delete": partial(_h_awx_template_delete, ctx),
    }
