"""Job lifecycle tools (launch/get/list/cancel/output/analysis)."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext
from awx_mcp_server.utils import analyze_job_failure, get_logger

logger = get_logger(__name__)

TOOLS: list[Tool] = [
    # Execution
    Tool(
        name="awx_job_launch",
        description="Launch/execute/run/start a new AWX job from a template. Creates a new job execution instance.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Job template ID to execute",
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables (JSON) to pass to playbook",
                },
                "limit": {
                    "type": "string",
                    "description": "Limit execution to specific hosts",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ansible tags to run",
                },
                "skip_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ansible tags to skip",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_job_get",
        description="Get specific AWX job metadata and summary details including status, timing, template info, and playbook name. Use this to check a single job's current state, whether it succeeded or failed, and its start/finish times. Does NOT return console output or logs — use awx_job_stdout for that.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "number",
                    "description": "Job ID from job execution",
                },
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_jobs_list",
        description="Show/list/display/view recent AWX jobs, job execution history, completed jobs, running jobs, failed jobs, job status, job runs, playbook executions. Use this when user asks to 'show recent jobs', 'list jobs', 'view jobs', 'get jobs', 'display job history', 'see recent activity', 'check job status', or any query about AWX job executions with timestamps and results.",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status (successful, failed, running, etc.)",
                },
                "created_after": {
                    "type": "string",
                    "description": "Filter by created date (ISO format)",
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
        name="awx_job_cancel",
        description="Cancel/stop/abort a currently running AWX job execution. Use this when user asks to 'cancel job', 'stop job', 'abort job', 'kill job', or any request to halt a running job.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "number", "description": "Job ID"},
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_job_delete",
        description="Delete/remove an AWX job record from history. Use this when user asks to 'delete job', 'remove job', 'clean up job', or any request to permanently remove a job record.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "number", "description": "Job ID"},
            },
            "required": ["job_id"],
        },
    ),
    # Diagnostics
    Tool(
        name="awx_job_stdout",
        description="Show/display/view/get the console output, stdout, logs, or terminal output of an AWX job execution. Use this when user asks to 'show job output', 'view job logs', 'display console output', 'get job stdout', 'show what the job printed', 'see the playbook output', 'show execution log', or any request to see the text/log output produced by a job run.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "number",
                    "description": "Job ID to retrieve output for",
                },
                "format": {
                    "type": "string",
                    "description": "Output format (txt or json)",
                    "enum": ["txt", "json"],
                },
                "tail_lines": {
                    "type": "number",
                    "description": "Number of lines from end (omit to get all output)",
                },
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_job_events",
        description="Show/list/view/get detailed events, tasks, plays, and execution steps of an AWX job. Use this when user asks to 'show job events', 'view job tasks', 'list execution steps', 'see what tasks ran', 'show detailed job activity', 'view play-by-play execution', or any request about the individual task/play events within a job run. Can filter to show only failed events.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "number",
                    "description": "Job ID to retrieve events for",
                },
                "failed_only": {
                    "type": "boolean",
                    "description": "Show only failed events (default: false)",
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
            "required": ["job_id"],
        },
    ),
    Tool(
        name="awx_job_failure_summary",
        description="Analyze/diagnose/debug/troubleshoot why an AWX job failed and get actionable fix suggestions. Use this when user asks 'why did job fail', 'analyze failure', 'debug job error', 'show failure summary', 'what went wrong with job', 'diagnose job problem', 'troubleshoot job', or any request to understand and fix a failed job execution.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "number",
                    "description": "Job ID of the failed job to analyze",
                },
            },
            "required": ["job_id"],
        },
    ),
]


async def _h_awx_job_launch(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    # Get template to check allowlist
    async with client:
        template = await client.get_job_template(template_id)
        ctx.check_allowlist(env, template_id, template.name)

        job = await client.launch_job(
            template_id=template_id,
            extra_vars=arguments.get("extra_vars"),
            limit=arguments.get("limit"),
            tags=arguments.get("tags"),
            skip_tags=arguments.get("skip_tags"),
        )

    # Audit log
    logger.info(
        "job_launched",
        environment=env.name,
        template=template.name,
        job_id=job.id,
    )

    result = "✓ Job launched successfully\n\n"
    result += f"Job ID: {job.id}\n"
    result += f"Name: {job.name}\n"
    result += f"Status: {job.status.value}\n"
    result += f"Playbook: {job.playbook}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_job_get(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        job = await client.get_job(job_id)

    result = f"Job {job_id} Details:\n\n"
    result += f"Name: {job.name}\n"
    result += f"Status: {job.status.value}\n"
    result += f"Playbook: {job.playbook}\n"
    if job.started:
        result += f"Started: {job.started.isoformat()}\n"
    if job.finished:
        result += f"Finished: {job.finished.isoformat()}\n"
    if job.elapsed:
        result += f"Elapsed: {job.elapsed}s\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_jobs_list(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()

    async with client:
        jobs = await client.list_jobs(
            status=arguments.get("status"),
            created_after=arguments.get("created_after"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Recent Jobs ({len(jobs)}):\n\n"
    for job in jobs:
        result += f"ID: {job.id} - {job.name}\n"
        result += f"  Status: {job.status.value}\n"
        result += f"  Playbook: {job.playbook}\n"
        if job.started:
            result += f"  Started: {job.started.isoformat()}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_job_cancel(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        await client.cancel_job(job_id)

    return [TextContent(type="text", text=f"Job {job_id} cancellation requested")]


async def _h_awx_job_delete(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        # RestAWXClient has no delete_job; go through rest_client
        # like every other delete_* tool (was an AttributeError bug).
        await client.delete_job(job_id)

    return [TextContent(type="text", text=f"Job {job_id} deleted successfully")]


async def _h_awx_job_stdout(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    job_id = arguments["job_id"]
    format = arguments.get("format", "txt")
    tail_lines = arguments.get("tail_lines")

    async with client:
        stdout = await client.get_job_stdout(job_id, format, tail_lines)

    result = f"Job {job_id} Output:\n\n{stdout}"
    return [TextContent(type="text", text=result)]


async def _h_awx_job_events(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    job_id = arguments["job_id"]
    failed_only = arguments.get("failed_only", False)

    async with client:
        events = await client.get_job_events(
            job_id=job_id,
            failed_only=failed_only,
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 100),
        )

    result = f"Job {job_id} Events ({len(events)}):\n\n"
    for event in events:
        if event.task:
            result += f"Task: {event.task}\n"
        if event.host:
            result += f"  Host: {event.host}\n"
        result += f"  Event: {event.event}\n"
        result += f"  Failed: {event.failed}\n"
        if event.stdout:
            result += f"  Output: {event.stdout[:200]}...\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_job_failure_summary(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    job_id = arguments["job_id"]

    async with client:
        # Get job events and stdout
        events = await client.get_job_events(job_id, failed_only=True)
        stdout = await client.get_job_stdout(job_id, "txt", 500)

    # Analyze failure
    analysis = analyze_job_failure(job_id, events, stdout)

    result = f"Job {job_id} Failure Analysis:\n\n"
    result += f"Category: {analysis.category.value}\n"
    result += f"Failed Events: {analysis.failed_events_count}\n\n"

    if analysis.task_name:
        result += f"Failed Task: {analysis.task_name}\n"
    if analysis.play_name:
        result += f"Play: {analysis.play_name}\n"
    if analysis.host:
        result += f"Host: {analysis.host}\n"

    if analysis.error_message:
        result += f"\nError Message:\n{analysis.error_message}\n"

    if analysis.suggested_fixes:
        result += "\n🔧 Suggested Fixes:\n\n"
        for i, fix in enumerate(analysis.suggested_fixes, 1):
            result += f"{i}. {fix}\n"

    return [TextContent(type="text", text=result)]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "awx_job_launch": partial(_h_awx_job_launch, ctx),
        "awx_job_get": partial(_h_awx_job_get, ctx),
        "awx_jobs_list": partial(_h_awx_jobs_list, ctx),
        "awx_job_cancel": partial(_h_awx_job_cancel, ctx),
        "awx_job_delete": partial(_h_awx_job_delete, ctx),
        "awx_job_stdout": partial(_h_awx_job_stdout, ctx),
        "awx_job_events": partial(_h_awx_job_events, ctx),
        "awx_job_failure_summary": partial(_h_awx_job_failure_summary, ctx),
    }
