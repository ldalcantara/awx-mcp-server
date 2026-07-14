"""Local ansible/playbook authoring and execution tools."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server import playbook_manager
from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    # ── Local Ansible Development Tools ──
    Tool(
        name="create_playbook",
        description="Create/write/generate an Ansible playbook YAML file locally. Use this when user asks to 'create a playbook', 'write a playbook', 'generate a playbook', 'make a new playbook', or wants to author Ansible YAML content before running it on AWX.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Playbook filename (e.g., 'deploy.yml')",
                },
                "content": {
                    "description": "Playbook content as YAML string, dict (single play), or list of plays",
                },
                "workspace": {
                    "type": "string",
                    "description": "Directory to save in (default: ~/.awx-mcp/playbooks)",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Overwrite if file exists (default: false)",
                },
            },
            "required": ["name", "content"],
        },
    ),
    Tool(
        name="validate_playbook",
        description="Validate/check/lint Ansible playbook syntax using ansible-playbook --syntax-check. Use this when user asks to 'validate playbook', 'check playbook syntax', 'lint playbook', 'verify playbook', or wants to ensure a playbook is syntactically correct before running it.",
        inputSchema={
            "type": "object",
            "properties": {
                "playbook": {
                    "type": "string",
                    "description": "Playbook filename or full path",
                },
                "workspace": {
                    "type": "string",
                    "description": "Workspace directory (if playbook is just a name)",
                },
                "inventory": {
                    "type": "string",
                    "description": "Inventory file/path for validation",
                },
            },
            "required": ["playbook"],
        },
    ),
    Tool(
        name="ansible_playbook",
        description="Execute/run an Ansible playbook locally for development and testing. Use this when user asks to 'run playbook locally', 'execute playbook', 'test playbook', 'dry-run playbook', or wants to run a playbook in their dev environment before pushing to AWX. Supports check mode (dry-run), extra vars, tags, and host limits.",
        inputSchema={
            "type": "object",
            "properties": {
                "playbook": {
                    "type": "string",
                    "description": "Playbook filename or full path",
                },
                "workspace": {
                    "type": "string",
                    "description": "Workspace directory",
                },
                "inventory": {
                    "type": "string",
                    "description": "Inventory file/string (default: localhost)",
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables dict to pass to playbook",
                },
                "limit": {
                    "type": "string",
                    "description": "Host limit pattern",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ansible tags to run",
                },
                "skip_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to skip",
                },
                "check_mode": {
                    "type": "boolean",
                    "description": "Dry-run mode (--check), default: false",
                },
                "verbose": {
                    "type": "number",
                    "description": "Verbosity level 0-4 (default: 0)",
                },
            },
            "required": ["playbook"],
        },
    ),
    Tool(
        name="ansible_task",
        description="Run an ad-hoc Ansible task/module locally. Use this when user asks to 'run ansible module', 'execute ad-hoc task', 'ping hosts', 'run shell command with ansible', 'test ansible module', or wants to run a single Ansible module without a playbook. Defaults to connection=local for localhost.",
        inputSchema={
            "type": "object",
            "properties": {
                "module": {
                    "type": "string",
                    "description": "Ansible module name (e.g., 'ping', 'shell', 'copy', 'debug')",
                },
                "args": {
                    "type": "string",
                    "description": "Module arguments string (e.g., 'msg=hello' for debug)",
                },
                "hosts": {
                    "type": "string",
                    "description": "Host pattern (default: localhost)",
                },
                "inventory": {
                    "type": "string",
                    "description": "Inventory file/string",
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables",
                },
                "connection": {
                    "type": "string",
                    "description": "Connection type (default: local)",
                },
                "become": {
                    "type": "boolean",
                    "description": "Use privilege escalation (sudo)",
                },
            },
            "required": ["module"],
        },
    ),
    Tool(
        name="ansible_role",
        description="Execute/run an Ansible role locally by generating a temporary playbook. Use this when user asks to 'run a role', 'execute role', 'test role locally', or wants to apply a specific role from their project without writing a full playbook.",
        inputSchema={
            "type": "object",
            "properties": {
                "role": {"type": "string", "description": "Role name or path"},
                "hosts": {
                    "type": "string",
                    "description": "Target hosts (default: localhost)",
                },
                "workspace": {
                    "type": "string",
                    "description": "Workspace directory containing roles/",
                },
                "inventory": {
                    "type": "string",
                    "description": "Inventory file/string",
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables to pass to role",
                },
                "connection": {
                    "type": "string",
                    "description": "Connection type (default: local)",
                },
            },
            "required": ["role"],
        },
    ),
    Tool(
        name="create_role_structure",
        description="Scaffold/generate/create an Ansible role directory structure with standard subdirectories (tasks, handlers, templates, files, vars, defaults, meta). Use this when user asks to 'create a role', 'scaffold a role', 'generate role skeleton', 'init role structure', or wants to set up a new role from scratch.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Role name"},
                "workspace": {
                    "type": "string",
                    "description": "Workspace where roles/ directory lives",
                },
                "include_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Subdirectories to include (default: all standard dirs)",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="list_playbooks",
        description="List/show/display all Ansible playbooks in the workspace or project directory. Use this when user asks to 'list playbooks', 'show my playbooks', 'what playbooks exist', 'find playbooks'.",
        inputSchema={
            "type": "object",
            "properties": {
                "workspace": {
                    "type": "string",
                    "description": "Workspace directory to scan (default: ~/.awx-mcp/playbooks)",
                },
            },
        },
    ),
    Tool(
        name="list_roles",
        description="List/show/display all Ansible roles in the workspace. Use this when user asks to 'list roles', 'show my roles', 'what roles exist'.",
        inputSchema={
            "type": "object",
            "properties": {
                "workspace": {
                    "type": "string",
                    "description": "Workspace directory (default: ~/.awx-mcp/playbooks)",
                },
            },
        },
    ),
    Tool(
        name="ansible_inventory",
        description="List/show Ansible inventory hosts and groups using ansible-inventory. Use this when user asks to 'list inventory hosts', 'show inventory groups', 'display local inventory', 'what hosts are in my inventory file'.",
        inputSchema={
            "type": "object",
            "properties": {
                "inventory": {
                    "type": "string",
                    "description": "Inventory file, path, or host list (default: localhost)",
                },
                "workspace": {
                    "type": "string",
                    "description": "Working directory",
                },
            },
        },
    ),
]


async def _h_create_playbook(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    pb_result = playbook_manager.create_playbook(
        name=arguments["name"],
        content=arguments["content"],
        workspace=arguments.get("workspace"),
        overwrite=arguments.get("overwrite", False),
    )
    if pb_result["status"] == "created":
        result = f"✅ Playbook created: {pb_result['name']}\n"
        result += f"Path: {pb_result['path']}\n"
        result += f"Plays: {pb_result['plays']}\n\n"
        result += f"Preview:\n```yaml\n{pb_result['preview']}\n```"
    else:
        result = f"❌ {pb_result['message']}"
    return [TextContent(type="text", text=result)]


async def _h_validate_playbook(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    val_result = await playbook_manager.validate_playbook(
        playbook=arguments["playbook"],
        workspace=arguments.get("workspace"),
        inventory=arguments.get("inventory"),
    )
    if val_result["status"] == "valid":
        result = f"✅ Playbook syntax is valid: {val_result['playbook']}\n"
        if val_result.get("output"):
            result += f"\n{val_result['output']}"
    elif val_result["status"] == "invalid":
        result = f"❌ Playbook has syntax errors: {val_result['playbook']}\n\n"
        result += f"Errors:\n{val_result['errors']}"
    else:
        result = f"❌ {val_result['message']}"
    return [TextContent(type="text", text=result)]


async def _h_ansible_playbook(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    exec_result = await playbook_manager.run_playbook(
        playbook=arguments["playbook"],
        workspace=arguments.get("workspace"),
        inventory=arguments.get("inventory"),
        extra_vars=arguments.get("extra_vars"),
        limit=arguments.get("limit"),
        tags=arguments.get("tags"),
        skip_tags=arguments.get("skip_tags"),
        check_mode=arguments.get("check_mode", False),
        verbose=arguments.get("verbose", 0),
    )
    if exec_result["status"] == "error":
        result = f"❌ {exec_result['message']}"
    else:
        mode = " (CHECK MODE)" if exec_result.get("check_mode") else ""
        status_icon = "✅" if exec_result["status"] == "successful" else "❌"
        result = f"{status_icon} Playbook execution{mode}: {exec_result['status']}\n"
        result += f"Playbook: {exec_result['playbook']}\n\n"
        result += f"Output:\n{exec_result['stdout']}"
        if exec_result.get("stderr"):
            result += f"\n\nStderr:\n{exec_result['stderr']}"
    return [TextContent(type="text", text=result)]


async def _h_ansible_task(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    task_result = await playbook_manager.run_adhoc_task(
        module=arguments["module"],
        args=arguments.get("args"),
        hosts=arguments.get("hosts", "localhost"),
        inventory=arguments.get("inventory"),
        extra_vars=arguments.get("extra_vars"),
        connection=arguments.get("connection", "local"),
        become=arguments.get("become", False),
    )
    if task_result["status"] == "error":
        result = f"❌ {task_result['message']}"
    else:
        status_icon = "✅" if task_result["status"] == "successful" else "❌"
        result = f"{status_icon} Ad-hoc task: {task_result['module']} on {task_result['hosts']}\n\n"
        result += f"Output:\n{task_result['stdout']}"
        if task_result.get("stderr"):
            result += f"\n\nStderr:\n{task_result['stderr']}"
    return [TextContent(type="text", text=result)]


async def _h_ansible_role(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    role_result = await playbook_manager.run_role(
        role=arguments["role"],
        hosts=arguments.get("hosts", "localhost"),
        workspace=arguments.get("workspace"),
        inventory=arguments.get("inventory"),
        extra_vars=arguments.get("extra_vars"),
        connection=arguments.get("connection", "local"),
    )
    if role_result["status"] == "error":
        result = f"❌ {role_result['message']}"
    else:
        status_icon = "✅" if role_result["status"] == "successful" else "❌"
        result = f"{status_icon} Role execution: {role_result['role']} - {role_result['status']}\n\n"
        result += f"Output:\n{role_result['stdout']}"
        if role_result.get("stderr"):
            result += f"\n\nStderr:\n{role_result['stderr']}"
    return [TextContent(type="text", text=result)]


async def _h_create_role_structure(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    role_result = playbook_manager.create_role_structure(
        name=arguments["name"],
        workspace=arguments.get("workspace"),
        include_dirs=arguments.get("include_dirs"),
    )
    if role_result["status"] == "created":
        result = f"✅ Role scaffolded: {role_result['role']}\n"
        result += f"Path: {role_result['path']}\n"
        result += f"Directories: {', '.join(role_result['directories'])}\n\n"
        result += "Files created:\n"
        for f in role_result["files"]:
            result += f"  - {f}\n"
    else:
        result = f"❌ {role_result['message']}"
    return [TextContent(type="text", text=result)]


async def _h_list_playbooks(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    pb_result = playbook_manager.list_playbooks(
        workspace=arguments.get("workspace"),
    )
    result = f"Playbooks in {pb_result['workspace']} ({pb_result['count']}):\n\n"
    for pb in pb_result["playbooks"]:
        plays_info = f" ({pb['plays']} plays)" if pb.get("plays") else ""
        result += f"  📄 {pb['name']}{plays_info} - {pb['size']} bytes\n"
    if not pb_result["playbooks"]:
        result += "  (none found)\n"
    return [TextContent(type="text", text=result)]


async def _h_list_roles(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    roles_result = playbook_manager.list_roles(
        workspace=arguments.get("workspace"),
    )
    result = f"Roles in {roles_result['workspace']} ({roles_result['count']}):\n\n"
    for role in roles_result["roles"]:
        result += f"  📁 {role['name']} - dirs: {', '.join(role['directories'])}\n"
    if not roles_result["roles"]:
        result += "  (none found)\n"
    return [TextContent(type="text", text=result)]


async def _h_ansible_inventory(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    inv_result = await playbook_manager.ansible_inventory_list(
        inventory=arguments.get("inventory", "localhost,"),
        workspace=arguments.get("workspace"),
    )
    if inv_result["status"] == "success":
        data = inv_result["data"]
        if isinstance(data, dict):
            import json as _json

            result = f"Inventory: {inv_result['inventory']}\n\n"
            result += _json.dumps(data, indent=2, default=str)
        else:
            result = str(data)
    else:
        result = f"❌ {inv_result['message']}"
    return [TextContent(type="text", text=result)]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "create_playbook": partial(_h_create_playbook, ctx),
        "validate_playbook": partial(_h_validate_playbook, ctx),
        "ansible_playbook": partial(_h_ansible_playbook, ctx),
        "ansible_task": partial(_h_ansible_task, ctx),
        "ansible_role": partial(_h_ansible_role, ctx),
        "create_role_structure": partial(_h_create_role_structure, ctx),
        "list_playbooks": partial(_h_list_playbooks, ctx),
        "list_roles": partial(_h_list_roles, ctx),
        "ansible_inventory": partial(_h_ansible_inventory, ctx),
    }
