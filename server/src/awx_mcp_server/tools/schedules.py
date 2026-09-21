"""Schedule tools — the whole /api/v2/schedules/ estate, not one template's slice.

A schedule is what makes AWX run something without a person: nightly patching,
an inventory sync, a project update. They all live in one collection keyed by
``unified_job_template``, so "what runs automatically?" is answered here rather
than by walking every template.

RRULE is the thing to get right. AWX accepts an iCal recurrence rule on a single
line, starting with ``DTSTART`` and carrying one ``RRULE``:

    DTSTART;TZID=America/New_York:20260812T050000 RRULE:INTERVAL=1;FREQ=WEEKLY;BYDAY=WE

Name the timezone in ``DTSTART;TZID=`` when the schedule should track local
time, including daylight saving; use a ``Z`` suffix for plain UTC.
"""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext

_RRULE_HELP = (
    "iCal recurrence rule on one line, e.g. "
    "'DTSTART;TZID=America/New_York:20260812T050000 "
    "RRULE:INTERVAL=1;FREQ=WEEKLY;BYDAY=WE'. Use DTSTART;TZID=<zone> to follow "
    "local time (and daylight saving), or a trailing Z for UTC."
)

TOOLS: list[Tool] = [
    Tool(
        name="awx_schedules_list",
        description=(
            "List AWX schedules — everything that runs automatically, across job "
            "templates, workflows, project updates and inventory sources. Use this "
            "when asked what is scheduled, what runs nightly/weekly, or when the "
            "next automatic run is. Optionally narrow to one template."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter schedules by name",
                },
                "unified_job_template": {
                    "type": "number",
                    "description": "Only schedules of this job template / workflow / project / inventory source ID",
                },
                "page": {"type": "number", "description": "Page number (default: 1)"},
                "page_size": {
                    "type": "number",
                    "description": "Page size (default: 25)",
                },
            },
        },
    ),
    Tool(
        name="awx_schedule_get",
        description="Get one AWX schedule by ID: what it runs, its recurrence rule, whether it is enabled, and the next run.",
        inputSchema={
            "type": "object",
            "properties": {
                "schedule_id": {"type": "number", "description": "Schedule ID"},
            },
            "required": ["schedule_id"],
        },
    ),
    Tool(
        name="awx_schedule_create",
        description="Create an AWX schedule so a job template, workflow, project update or inventory source runs automatically.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Schedule name"},
                "unified_job_template": {
                    "type": "number",
                    "description": "ID of the job template, workflow, project or inventory source to run",
                },
                "rrule": {"type": "string", "description": _RRULE_HELP},
                "description": {"type": "string", "description": "Description"},
                "enabled": {
                    "type": "boolean",
                    "description": "Whether the schedule is active (default: true)",
                },
                "extra_data": {
                    "type": "object",
                    "description": "Extra variables passed to the run, e.g. {'patch_reboot': true}",
                },
                "limit": {
                    "type": "string",
                    "description": "Host pattern to limit the run to",
                },
                "job_tags": {"type": "string", "description": "Comma-separated tags"},
                "skip_tags": {
                    "type": "string",
                    "description": "Comma-separated tags to skip",
                },
                "inventory": {
                    "type": "number",
                    "description": "Inventory ID, when the template prompts for one",
                },
            },
            "required": ["name", "unified_job_template", "rrule"],
        },
    ),
    Tool(
        name="awx_schedule_update",
        description="Update an AWX schedule (partial): change its recurrence rule, enable or disable it, or adjust the variables it passes.",
        inputSchema={
            "type": "object",
            "properties": {
                "schedule_id": {"type": "number", "description": "Schedule ID"},
                "name": {"type": "string", "description": "New name"},
                "rrule": {"type": "string", "description": _RRULE_HELP},
                "description": {"type": "string", "description": "New description"},
                "enabled": {
                    "type": "boolean",
                    "description": "Enable (true) or pause (false) the schedule",
                },
                "extra_data": {
                    "type": "object",
                    "description": "Extra variables passed to the run",
                },
                "limit": {"type": "string", "description": "Host pattern"},
                "job_tags": {"type": "string", "description": "Comma-separated tags"},
                "skip_tags": {
                    "type": "string",
                    "description": "Comma-separated tags to skip",
                },
            },
            "required": ["schedule_id"],
        },
    ),
    Tool(
        name="awx_schedule_delete",
        description="Delete an AWX schedule. The template it points at is untouched; only the automatic trigger goes away.",
        inputSchema={
            "type": "object",
            "properties": {
                "schedule_id": {"type": "number", "description": "Schedule ID"},
            },
            "required": ["schedule_id"],
        },
    ),
]


def _describe(sched: dict[str, Any], indent: str = "  ") -> str:
    """Render the fields that answer "what runs, when, and is it on?"."""
    target = sched.get("summary_fields", {}).get("unified_job_template", {})
    out = ""
    if target:
        kind = target.get("unified_job_type", "unknown")
        out += f"{indent}Runs: {target.get('name', 'unknown')} ({kind})\n"
    out += (
        f"{indent}Enabled: {'yes' if sched.get('enabled', True) else 'no (paused)'}\n"
    )
    if sched.get("rrule"):
        out += f"{indent}Rule: {sched['rrule']}\n"
    if sched.get("next_run"):
        out += f"{indent}Next run: {sched['next_run']}\n"
    if sched.get("description"):
        out += f"{indent}Description: {sched['description']}\n"
    if sched.get("extra_data"):
        out += f"{indent}Extra variables: {sched['extra_data']}\n"
    if sched.get("limit"):
        out += f"{indent}Limit: {sched['limit']}\n"
    return out


async def _h_awx_schedules_list(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    async with client:
        schedules = await client.list_schedules(
            name_filter=arguments.get("filter"),
            unified_job_template=arguments.get("unified_job_template"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Schedules ({len(schedules)}):\n\n"
    for sched in schedules:
        result += f"ID: {sched['id']} - {sched['name']}\n"
        result += _describe(sched)
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_schedule_get(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    schedule_id = arguments["schedule_id"]

    async with client:
        sched = await client.get_schedule(schedule_id)

    result = f"Schedule {schedule_id}:\n\n"
    result += f"Name: {sched['name']}\n"
    result += _describe(sched, indent="")

    return [TextContent(type="text", text=result)]


async def _h_awx_schedule_create(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    async with client:
        sched = await client.create_schedule(
            name=arguments["name"],
            unified_job_template=arguments["unified_job_template"],
            rrule=arguments["rrule"],
            description=arguments.get("description", ""),
            enabled=arguments.get("enabled", True),
            extra_data=arguments.get("extra_data"),
            limit=arguments.get("limit"),
            job_tags=arguments.get("job_tags"),
            skip_tags=arguments.get("skip_tags"),
            inventory=arguments.get("inventory"),
        )

    result = "Schedule created successfully\n\n"
    result += f"ID: {sched['id']}\n"
    result += f"Name: {sched['name']}\n"
    result += _describe(sched)

    return [TextContent(type="text", text=result)]


async def _h_awx_schedule_update(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    schedule_id = arguments["schedule_id"]
    fields = {k: v for k, v in arguments.items() if k != "schedule_id"}

    async with client:
        sched = await client.update_schedule(schedule_id, **fields)

    result = f"Schedule {schedule_id} updated successfully\n\n"
    result += f"Name: {sched['name']}\n"
    result += _describe(sched, indent="")

    return [TextContent(type="text", text=result)]


async def _h_awx_schedule_delete(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    _env, client = ctx.get_active_client()
    schedule_id = arguments["schedule_id"]

    async with client:
        await client.delete_schedule(schedule_id)

    return [
        TextContent(
            type="text",
            text=(
                f"Schedule {schedule_id} deleted successfully\n\n"
                "The template it pointed at is unchanged; it simply no longer "
                "runs on its own.\n"
            ),
        )
    ]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Return this module's tool name -> handler mapping."""
    return {
        "awx_schedules_list": partial(_h_awx_schedules_list, ctx),
        "awx_schedule_get": partial(_h_awx_schedule_get, ctx),
        "awx_schedule_create": partial(_h_awx_schedule_create, ctx),
        "awx_schedule_update": partial(_h_awx_schedule_update, ctx),
        "awx_schedule_delete": partial(_h_awx_schedule_delete, ctx),
    }
