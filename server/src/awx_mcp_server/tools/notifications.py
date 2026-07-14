"""Notification-template tools and template associations."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    # Notification Templates
    Tool(
        name="awx_notification_templates_list",
        description="List AWX notification templates. Shows configured notifications (Slack, email, webhook, etc.) and their types.",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter notification templates by name",
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
        name="awx_notification_template_get",
        description="Get details of a specific AWX notification template by ID, including its type, configuration, and custom messages.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Notification template ID",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_notification_template_create",
        description="Create a new AWX notification template (Slack, email, webhook, etc.).",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Notification template name",
                },
                "organization": {
                    "type": "number",
                    "description": "Organization ID",
                },
                "notification_type": {
                    "type": "string",
                    "description": "Notification type",
                    "enum": [
                        "slack",
                        "email",
                        "webhook",
                        "pagerduty",
                        "grafana",
                        "twilio",
                        "irc",
                        "mattermost",
                        "rocketchat",
                    ],
                },
                "notification_configuration": {
                    "type": "object",
                    "description": "Type-specific config (e.g., {token, channels, hex_color} for Slack, {url} for webhook)",
                },
                "description": {"type": "string", "description": "Description"},
                "messages": {
                    "type": "object",
                    "description": "Custom messages per event, e.g., {started: {message: '...'}, success: {message: '...'}, error: {message: '...'}}",
                },
            },
            "required": ["name", "organization", "notification_type"],
        },
    ),
    Tool(
        name="awx_notification_template_test",
        description="Send a test notification from a notification template. Useful for verifying the template configuration (Slack channel, webhook URL, etc.) is working.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Notification template ID to test",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_notifications_list",
        description="List sent notification history/delivery log. Shows notification status (pending, successful, failed), recipients, and errors. Can filter by notification template or status.",
        inputSchema={
            "type": "object",
            "properties": {
                "notification_template_id": {
                    "type": "number",
                    "description": "Filter by notification template ID",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (pending, successful, failed)",
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
        name="awx_notification_template_update",
        description="Update an existing AWX notification template. Only provided fields are changed (partial update).",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Notification template ID",
                },
                "name": {"type": "string", "description": "New name"},
                "description": {
                    "type": "string",
                    "description": "New description",
                },
                "notification_configuration": {
                    "type": "object",
                    "description": "Updated type-specific config",
                },
                "messages": {
                    "type": "object",
                    "description": "Updated custom messages per event",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_notification_template_delete",
        description="Delete an AWX notification template.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Notification template ID to delete",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_job_template_notifications_list",
        description="List notification templates associated with a job template, showing which notifications fire on started, success, and error events.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Job template ID",
                },
            },
            "required": ["template_id"],
        },
    ),
    Tool(
        name="awx_job_template_notification_associate",
        description="Associate/attach a notification template to a job template for a specific event (started, success, or error).",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Job template ID",
                },
                "notification_template_id": {
                    "type": "number",
                    "description": "Notification template ID to attach",
                },
                "event": {
                    "type": "string",
                    "description": "Event to trigger notification on",
                    "enum": ["started", "success", "error"],
                },
            },
            "required": ["template_id", "notification_template_id", "event"],
        },
    ),
    Tool(
        name="awx_job_template_notification_disassociate",
        description="Disassociate/remove a notification template from a job template for a specific event (started, success, or error).",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Job template ID",
                },
                "notification_template_id": {
                    "type": "number",
                    "description": "Notification template ID to remove",
                },
                "event": {
                    "type": "string",
                    "description": "Event to remove notification from",
                    "enum": ["started", "success", "error"],
                },
            },
            "required": ["template_id", "notification_template_id", "event"],
        },
    ),
    Tool(
        name="awx_workflow_template_notifications_list",
        description="List notification templates associated with a workflow job template, showing which notifications fire on started, success, and error events.",
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
        name="awx_workflow_template_notification_associate",
        description="Associate/attach a notification template to a workflow job template for a specific event (started, success, or error).",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID",
                },
                "notification_template_id": {
                    "type": "number",
                    "description": "Notification template ID to attach",
                },
                "event": {
                    "type": "string",
                    "description": "Event to trigger notification on",
                    "enum": ["started", "success", "error"],
                },
            },
            "required": ["template_id", "notification_template_id", "event"],
        },
    ),
    Tool(
        name="awx_workflow_template_notification_disassociate",
        description="Disassociate/remove a notification template from a workflow job template for a specific event (started, success, or error).",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "number",
                    "description": "Workflow job template ID",
                },
                "notification_template_id": {
                    "type": "number",
                    "description": "Notification template ID to remove",
                },
                "event": {
                    "type": "string",
                    "description": "Event to remove notification from",
                    "enum": ["started", "success", "error"],
                },
            },
            "required": ["template_id", "notification_template_id", "event"],
        },
    ),
]


# Notification Templates
async def _h_awx_notification_templates_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        templates = await client.list_notification_templates(
            name_filter=arguments.get("filter"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Notification Templates ({len(templates)}):\n\n"
    for tmpl in templates:
        result += f"ID: {tmpl['id']} - {tmpl['name']}\n"
        result += f"  Type: {tmpl.get('notification_type', 'unknown')}\n"
        if tmpl.get("description"):
            result += f"  Description: {tmpl['description']}\n"
        if tmpl.get("organization"):
            org_name = (
                tmpl.get("summary_fields", {}).get("organization", {}).get("name")
            )
            if org_name:
                result += f"  Organization: {org_name}\n"
        config = tmpl.get("notification_configuration", {})
        if config.get("channels"):
            result += f"  Channels: {', '.join(config['channels'])}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_notification_template_get(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        tmpl = await client.get_notification_template(template_id)

    result = f"Notification Template {template_id}:\n\n"
    result += f"Name: {tmpl['name']}\n"
    result += f"Type: {tmpl.get('notification_type', 'unknown')}\n"
    if tmpl.get("description"):
        result += f"Description: {tmpl['description']}\n"
    org_name = tmpl.get("summary_fields", {}).get("organization", {}).get("name")
    if org_name:
        result += f"Organization: {org_name}\n"

    config = tmpl.get("notification_configuration", {})
    result += "\nConfiguration:\n"
    for key, value in config.items():
        if key == "token":
            result += f"  {key}: (encrypted)\n"
        else:
            result += f"  {key}: {value}\n"

    messages = tmpl.get("messages", {})
    if messages:
        result += "\nCustom Messages:\n"
        for event, msg in messages.items():
            if event == "workflow_approval":
                continue
            if isinstance(msg, dict) and msg.get("message"):
                result += f"  {event}: {msg['message']}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_notification_template_create(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    async with client:
        tmpl = await client.create_notification_template(
            name=arguments["name"],
            organization=arguments["organization"],
            notification_type=arguments["notification_type"],
            notification_configuration=arguments.get("notification_configuration"),
            description=arguments.get("description", ""),
            messages=arguments.get("messages"),
        )

    result = "Notification template created successfully\n\n"
    result += f"ID: {tmpl['id']}\n"
    result += f"Name: {tmpl['name']}\n"
    result += f"Type: {tmpl.get('notification_type')}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_notification_template_test(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        notif = await client.test_notification_template(template_id)

    result = "Test notification sent\n\n"
    result += f"Notification ID: {notif.get('id')}\n"
    result += f"Status: {notif.get('status')}\n"
    result += f"Type: {notif.get('notification_type')}\n"
    result += f"Recipients: {notif.get('recipients')}\n"
    result += f"Subject: {notif.get('subject')}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_notifications_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()

    async with client:
        notifications = await client.list_notifications(
            notification_template_id=arguments.get("notification_template_id"),
            status=arguments.get("status"),
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 25),
        )

    result = f"Notifications ({len(notifications)}):\n\n"
    for n in notifications:
        tmpl_name = (
            n.get("summary_fields", {})
            .get("notification_template", {})
            .get("name", "Unknown")
        )
        result += f"ID: {n['id']} - {tmpl_name}\n"
        result += f"  Status: {n.get('status')}\n"
        result += f"  Type: {n.get('notification_type')}\n"
        result += f"  Created: {n.get('created')}\n"
        result += f"  Recipients: {n.get('recipients')}\n"
        if n.get("subject"):
            result += f"  Subject: {n['subject'][:100]}\n"
        if n.get("error"):
            result += f"  Error: {n['error']}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_notification_template_update(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments.pop("template_id")

    async with client:
        tmpl = await client.update_notification_template(
            template_id,
            name=arguments.get("name"),
            description=arguments.get("description"),
            notification_configuration=arguments.get("notification_configuration"),
            messages=arguments.get("messages"),
        )

    result = f"Notification template {template_id} updated\n\n"
    result += f"Name: {tmpl['name']}\n"
    result += f"Type: {tmpl.get('notification_type')}\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_notification_template_delete(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        await client.delete_notification_template(template_id)

    return [
        TextContent(
            type="text",
            text=f"Notification template {template_id} deleted successfully",
        )
    ]


async def _h_awx_job_template_notifications_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        started = await client.list_job_template_notification_templates(
            template_id, "started"
        )
        success = await client.list_job_template_notification_templates(
            template_id, "success"
        )
        error = await client.list_job_template_notification_templates(
            template_id, "error"
        )

    result = f"Job Template {template_id} Notifications:\n\n"
    for event_name, notifs in [
        ("Started", started),
        ("Success", success),
        ("Error", error),
    ]:
        result += f"{event_name} ({len(notifs)}):\n"
        if notifs:
            for n in notifs:
                result += f"  ID: {n['id']} - {n['name']} ({n.get('notification_type', 'unknown')})\n"
        else:
            result += "  (none)\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_job_template_notification_associate(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]
    notification_id = arguments["notification_template_id"]
    event = arguments["event"]

    async with client:
        await client.associate_job_template_notification(
            template_id, notification_id, event
        )

    return [
        TextContent(
            type="text",
            text=f"Notification template {notification_id} associated with job template {template_id} for '{event}' event",
        )
    ]


async def _h_awx_job_template_notification_disassociate(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]
    notification_id = arguments["notification_template_id"]
    event = arguments["event"]

    async with client:
        await client.disassociate_job_template_notification(
            template_id, notification_id, event
        )

    return [
        TextContent(
            type="text",
            text=f"Notification template {notification_id} disassociated from job template {template_id} for '{event}' event",
        )
    ]


async def _h_awx_workflow_template_notifications_list(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]

    async with client:
        started = await client.list_workflow_template_notification_templates(
            template_id, "started"
        )
        success = await client.list_workflow_template_notification_templates(
            template_id, "success"
        )
        error = await client.list_workflow_template_notification_templates(
            template_id, "error"
        )

    result = f"Workflow Job Template {template_id} Notifications:\n\n"
    for event_name, notifs in [
        ("Started", started),
        ("Success", success),
        ("Error", error),
    ]:
        result += f"{event_name} ({len(notifs)}):\n"
        if notifs:
            for n in notifs:
                result += f"  ID: {n['id']} - {n['name']} ({n.get('notification_type', 'unknown')})\n"
        else:
            result += "  (none)\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _h_awx_workflow_template_notification_associate(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]
    notification_id = arguments["notification_template_id"]
    event = arguments["event"]

    async with client:
        await client.associate_workflow_template_notification(
            template_id, notification_id, event
        )

    return [
        TextContent(
            type="text",
            text=f"Notification template {notification_id} associated with workflow template {template_id} for '{event}' event",
        )
    ]


async def _h_awx_workflow_template_notification_disassociate(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    env, client = ctx.get_active_client()
    template_id = arguments["template_id"]
    notification_id = arguments["notification_template_id"]
    event = arguments["event"]

    async with client:
        await client.disassociate_workflow_template_notification(
            template_id, notification_id, event
        )

    return [
        TextContent(
            type="text",
            text=f"Notification template {notification_id} disassociated from workflow template {template_id} for '{event}' event",
        )
    ]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "awx_notification_templates_list": partial(
            _h_awx_notification_templates_list, ctx
        ),
        "awx_notification_template_get": partial(_h_awx_notification_template_get, ctx),
        "awx_notification_template_create": partial(
            _h_awx_notification_template_create, ctx
        ),
        "awx_notification_template_test": partial(
            _h_awx_notification_template_test, ctx
        ),
        "awx_notifications_list": partial(_h_awx_notifications_list, ctx),
        "awx_notification_template_update": partial(
            _h_awx_notification_template_update, ctx
        ),
        "awx_notification_template_delete": partial(
            _h_awx_notification_template_delete, ctx
        ),
        "awx_job_template_notifications_list": partial(
            _h_awx_job_template_notifications_list, ctx
        ),
        "awx_job_template_notification_associate": partial(
            _h_awx_job_template_notification_associate, ctx
        ),
        "awx_job_template_notification_disassociate": partial(
            _h_awx_job_template_notification_disassociate, ctx
        ),
        "awx_workflow_template_notifications_list": partial(
            _h_awx_workflow_template_notifications_list, ctx
        ),
        "awx_workflow_template_notification_associate": partial(
            _h_awx_workflow_template_notification_associate, ctx
        ),
        "awx_workflow_template_notification_disassociate": partial(
            _h_awx_workflow_template_notification_disassociate, ctx
        ),
    }
