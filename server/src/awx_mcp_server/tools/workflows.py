"""Workflow job-template and workflow-job tools."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext
from awx_mcp_server.utils import get_logger

logger = get_logger(__name__)

TOOLS: list[Tool] = [
    # ── Workflow Job Templates ──
    Tool(
        name="awx_workflow_templates_list",
        description="List AWX workflow job templates. Workflow templates define multi-step automation pipelines that chain multiple job templates together. Use this when user asks to 'list workflows', 'show workflow templates', 'what workflows exist'.",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter workflow templates by name",
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
        name="awx_workflow_template_get",
        description="Get details of a specific AWX workflow job template by ID, including its configuration, launch options, schedule info, and status.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_workflow_job_launch",
        description="Launch/execute/run a workflow job from a workflow job template. Creates a new workflow job that orchestrates multiple steps.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID to execute",
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables (JSON) to pass to the workflow",
                },
                "limit": {
                    "type": "string",
                    "description": "Limit execution to specific hosts",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job tags to apply",
                },
                "skip_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job tags to skip",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_workflow_job_get",
        description="Get status and details of a specific AWX workflow job execution, including timing, launch type, and failure explanation.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "number", "description": "Workflow job ID"},
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_workflow_jobs_list",
        description="List recent AWX workflow job executions and their statuses. Use this to see workflow run history.",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status (successful, failed, running, etc.)",
                },
                "workflow_template_id": {
                    "type": "number",
                    "description": "Filter by workflow job template ID",
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
        name="awx_workflow_job_cancel",
        description="Cancel/stop a running AWX workflow job execution.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "number",
                    "description": "Workflow job ID to cancel",
                },
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_workflow_job_nodes",
        description="Get the individual step/node details of an AWX workflow job execution. Shows each node's job template, status, elapsed time, and connection graph (success/failure/always paths). Use this to see which steps passed or failed in a workflow run.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "number", "description": "Workflow job ID"},
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                },
                "page_size": {
                    "type": "number",
                    "description": "Page size (default: 100)",
                },
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_workflow_job_delete",
        description="Delete an AWX workflow job record from history.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "number",
                    "description": "Workflow job ID to delete",
                },
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_workflow_job_relaunch",
        description="Relaunch/rerun a previous AWX workflow job execution. Creates a new workflow job from the same template with the same parameters.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "number",
                    "description": "Workflow job ID to relaunch",
                },
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_workflow_template_nodes",
        description="Get the workflow job template node definitions — the graph of steps that make up the workflow template. Shows which job templates/projects/inventory sources are chained together and how (success/failure/always paths).",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID",
                },
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                },
                "page_size": {
                    "type": "number",
                    "description": "Page size (default: 100)",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_workflow_template_survey",
        description="Get the survey spec for a workflow job template. Shows survey questions that are prompted when launching the workflow.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_workflow_template_schedules",
        description="List schedules configured for a workflow job template. Shows when the workflow is set to run automatically.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID",
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
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_workflow_template_launch_config",
        description="Get the launch configuration for a workflow job template. Shows which fields can be prompted on launch (inventory, limit, variables, etc.) and their defaults.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID",
                },
            },
            "required": ["template_id"],
        },
    ),
]


# --- Migrated tool handlers (registry pattern) ---
async def _h_awx_workflow_templates_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        templates = await client.list_workflow_job_templates(
            name_filter=arguments.get("filter"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Workflow Job Templates ({len(templates)}):\n\n"
    for tmpl in templates:
        result += f"ID: {tmpl.id} - {tmpl.name}\n"
        if tmpl.description:
            result += f"  Description: {tmpl.description}\n"
        if tmpl.status:
            result += f"  Status: {tmpl.status}\n"
        if tmpl.last_job_run:
            result += f"  Last Run: {tmpl.last_job_run.isoformat()}\n"
        if tmpl.next_job_run:
            result += f"  Next Run: {tmpl.next_job_run.isoformat()}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_template_get(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        tmpl = await client.get_workflow_job_template(template_id)

    result = f"Workflow Job Template {template_id}:\n\n"
    result += f"Name: {tmpl.name}\n"
    if tmpl.description:
        result += f"Description: {tmpl.description}\n"
    if tmpl.organization:
        result += f"Organization: {tmpl.organization}\n"
    if tmpl.inventory:
        result += f"Inventory: {tmpl.inventory}\n"
    if tmpl.limit:
        result += f"Limit: {tmpl.limit}\n"
    if tmpl.status:
        result += f"Status: {tmpl.status}\n"
    result += f"Survey Enabled: {tmpl.survey_enabled}\n"
    result += f"Allow Simultaneous: {tmpl.allow_simultaneous}\n"
    if tmpl.last_job_run:
        result += f"Last Run: {tmpl.last_job_run.isoformat()}\n"
    if tmpl.next_job_run:
        result += f"Next Run: {tmpl.next_job_run.isoformat()}\n"
    result += "\nLaunch Options:\n"
    result += f"  Ask Variables: {tmpl.ask_variables_on_launch}\n"
    result += f"  Ask Inventory: {tmpl.ask_inventory_on_launch}\n"
    result += f"  Ask Limit: {tmpl.ask_limit_on_launch}\n"
    result += f"  Ask Tags: {tmpl.ask_tags_on_launch}\n"
    result += f"  Ask Skip Tags: {tmpl.ask_skip_tags_on_launch}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_job_launch(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        tmpl = await client.get_workflow_job_template(template_id)
        ctx.check_allowlist(env, template_id, tmpl.name)

        wf_job = await client.launch_workflow_job(
            template_id=template_id,
            extra_vars=arguments.get("extra_vars"),
            limit=arguments.get("limit"),
            tags=arguments.get("tags"),
            skip_tags=arguments.get("skip_tags"),
        )

    logger.info(
        "workflow_job_launched",
        environment=env.name,
        template=tmpl.name,
        job_id=wf_job.id,
    )

    result = "✓ Workflow job launched successfully\n\n"
    result += f"Workflow Job ID: {wf_job.id}\n"
    result += f"Name: {wf_job.name}\n"
    result += f"Status: {wf_job.status.value}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_job_get(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        wf_job = await client.get_workflow_job(job_id)

    result = f"Workflow Job {job_id} Details:\n\n"
    result += f"Name: {wf_job.name}\n"
    result += f"Status: {wf_job.status.value}\n"
    result += f"Failed: {wf_job.failed}\n"
    if wf_job.workflow_job_template:
        result += f"Template ID: {wf_job.workflow_job_template}\n"
    if wf_job.launch_type:
        result += f"Launch Type: {wf_job.launch_type}\n"
    if wf_job.started:
        result += f"Started: {wf_job.started.isoformat()}\n"
    if wf_job.finished:
        result += f"Finished: {wf_job.finished.isoformat()}\n"
    if wf_job.elapsed:
        result += f"Elapsed: {wf_job.elapsed}s\n"
    if wf_job.limit:
        result += f"Limit: {wf_job.limit}\n"
    if wf_job.job_explanation:
        result += f"\nExplanation: {wf_job.job_explanation}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_jobs_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()

    async with client:
        wf_jobs = await client.list_workflow_jobs(
            status=arguments.get("status"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
            workflow_template_id=arguments.get("workflow_template_id"),
        )

    result = f"Workflow Jobs ({len(wf_jobs)}):\n\n"
    for wf_job in wf_jobs:
        result += f"ID: {wf_job.id} - {wf_job.name}\n"
        result += f"  Status: {wf_job.status.value}\n"
        if wf_job.launch_type:
            result += f"  Launch Type: {wf_job.launch_type}\n"
        if wf_job.started:
            result += f"  Started: {wf_job.started.isoformat()}\n"
        if wf_job.finished:
            result += f"  Finished: {wf_job.finished.isoformat()}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_job_cancel(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        await client.cancel_workflow_job(job_id)

    return [
        TextContent(
            type="text",
            text=f"Workflow job {job_id} cancellation requested",
        )
    ]


async def _h_awx_workflow_job_nodes(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        nodes = await client.get_workflow_job_nodes(
            job_id=job_id,
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 100),
        )

    result = f"Workflow Job {job_id} Nodes ({len(nodes)}):\n\n"
    for node in nodes:
        # Extract names from summary_fields
        sf = node.summary_fields
        template_name = sf.get("unified_job_template", {}).get("name", "Unknown")
        job_type = sf.get("unified_job_template", {}).get("unified_job_type", "unknown")
        job_info = sf.get("job", {})
        job_status = job_info.get("status", "unknown")
        job_failed = job_info.get("failed", False)
        job_elapsed = job_info.get("elapsed")
        child_job_id = node.job

        status_icon = (
            "✗" if job_failed else ("✓" if job_status == "successful" else "●")
        )
        result += f"{status_icon} Node: {template_name} ({job_type})\n"
        if child_job_id:
            result += f"  Job ID: {child_job_id} | Status: {job_status}"
            if job_elapsed is not None:
                result += f" | Elapsed: {job_elapsed}s"
            result += "\n"
        if node.do_not_run:
            result += "  (skipped)\n"
        connections = []
        if node.success_nodes:
            connections.append(f"success -> {node.success_nodes}")
        if node.failure_nodes:
            connections.append(f"failure -> {node.failure_nodes}")
        if node.always_nodes:
            connections.append(f"always -> {node.always_nodes}")
        if connections:
            result += f"  Connections: {', '.join(connections)}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_job_delete(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        await client.delete_workflow_job(job_id)

    return [
        TextContent(type="text", text=f"Workflow job {job_id} deleted successfully")
    ]


async def _h_awx_workflow_job_relaunch(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        wf_job = await client.relaunch_workflow_job(job_id)

    result = "Workflow job relaunched successfully\n\n"
    result += f"New Workflow Job ID: {wf_job.id}\n"
    result += f"Name: {wf_job.name}\n"
    result += f"Status: {wf_job.status.value}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_template_nodes(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        nodes = await client.get_workflow_job_template_nodes(
            template_id,
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 100),
        )

    result = f"Workflow Template {template_id} Nodes ({len(nodes)}):\n\n"
    for node in nodes:
        sf = node.get("summary_fields", {})
        ujt = sf.get("unified_job_template", {})
        template_name = ujt.get("name", "Unknown")
        job_type = ujt.get("unified_job_type", "unknown")

        result += f"Node {node['id']}: {template_name} ({job_type})\n"
        connections = []
        if node.get("success_nodes"):
            connections.append(f"success -> {node['success_nodes']}")
        if node.get("failure_nodes"):
            connections.append(f"failure -> {node['failure_nodes']}")
        if node.get("always_nodes"):
            connections.append(f"always -> {node['always_nodes']}")
        if connections:
            result += f"  Connections: {', '.join(connections)}\n"
        if node.get("all_parents_must_converge"):
            result += "  All parents must converge: True\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_template_survey(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        survey = await client.get_workflow_job_template_survey(template_id)

    spec = survey.get("spec", [])
    if not spec:
        result = (
            f"Workflow Template {template_id} has no survey questions configured.\n"
        )
    else:
        result = f"Workflow Template {template_id} Survey ({len(spec)} questions):\n\n"
        if survey.get("name"):
            result += f"Name: {survey['name']}\n"
        if survey.get("description"):
            result += f"Description: {survey['description']}\n"
        result += "\n"
        for q in spec:
            required = " (required)" if q.get("required") else ""
            result += f"Variable: {q.get('variable')}{required}\n"
            result += f"  Question: {q.get('question_name', '')}\n"
            result += f"  Type: {q.get('type', 'text')}\n"
            if q.get("default"):
                result += f"  Default: {q['default']}\n"
            if q.get("choices"):
                result += f"  Choices: {q['choices']}\n"
            result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_template_schedules(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        schedules = await client.list_workflow_job_template_schedules(
            template_id,
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Workflow Template {template_id} Schedules ({len(schedules)}):\n\n"
    for s in schedules:
        result += f"ID: {s['id']} - {s['name']}\n"
        if s.get("description"):
            result += f"  Description: {s['description']}\n"
        result += f"  Enabled: {s.get('enabled', False)}\n"
        result += f"  RRule: {s.get('rrule', 'N/A')}\n"
        if s.get("next_run"):
            result += f"  Next Run: {s['next_run']}\n"
        if s.get("dtstart"):
            result += f"  Start: {s['dtstart']}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_template_launch_config(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        config = await client.get_workflow_job_template_launch_config(template_id)

    result = f"Workflow Template {template_id} Launch Configuration:\n\n"
    result += f"Can Start Without User Input: {config.get('can_start_without_user_input', False)}\n"
    result += f"Survey Enabled: {config.get('survey_enabled', False)}\n"
    result += f"Variables Needed: {config.get('variables_needed_to_start', [])}\n\n"

    result += "Prompt Options:\n"
    for key in [
        "ask_inventory_on_launch",
        "ask_limit_on_launch",
        "ask_scm_branch_on_launch",
        "ask_variables_on_launch",
        "ask_labels_on_launch",
        "ask_tags_on_launch",
        "ask_skip_tags_on_launch",
    ]:
        if config.get(key):
            result += f"  {key}: True\n"

    defaults = config.get("defaults", {})
    if defaults:
        result += "\nDefaults:\n"
        for key, value in defaults.items():
            if value is not None:
                result += f"  {key}: {value}\n"

    missing = config.get("node_templates_missing", [])
    if missing:
        result += f"\nMissing Node Templates: {missing}\n"

    return [TextContent(type="text", text=result)]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "awx_workflow_templates_list": partial(_h_awx_workflow_templates_list, ctx),
        "awx_workflow_template_get": partial(_h_awx_workflow_template_get, ctx),
        "awx_workflow_job_launch": partial(_h_awx_workflow_job_launch, ctx),
        "awx_workflow_job_get": partial(_h_awx_workflow_job_get, ctx),
        "awx_workflow_jobs_list": partial(_h_awx_workflow_jobs_list, ctx),
        "awx_workflow_job_cancel": partial(_h_awx_workflow_job_cancel, ctx),
        "awx_workflow_job_nodes": partial(_h_awx_workflow_job_nodes, ctx),
        "awx_workflow_job_delete": partial(_h_awx_workflow_job_delete, ctx),
        "awx_workflow_job_relaunch": partial(_h_awx_workflow_job_relaunch, ctx),
        "awx_workflow_template_nodes": partial(_h_awx_workflow_template_nodes, ctx),
        "awx_workflow_template_survey": partial(_h_awx_workflow_template_survey, ctx),
        "awx_workflow_template_schedules": partial(
            _h_awx_workflow_template_schedules, ctx
        ),
        "awx_workflow_template_launch_config": partial(
            _h_awx_workflow_template_launch_config, ctx
        ),
    }
