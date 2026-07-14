"""Local project-registry and git tools."""

from functools import partial
from typing import Any

from mcp.types import TextContent, Tool

from awx_mcp_server import project_registry
from awx_mcp_server.tools.context import ToolContext

TOOLS: list[Tool] = [
    # ── Project Registry Tools ──
    Tool(
        name="register_project",
        description="Register/add a local Ansible project directory for easy reuse. Use this when user asks to 'register project', 'add project', 'set up project', 'configure my ansible project'. Auto-detects git remote URL, inventory, and default playbook.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project alias name"},
                "path": {
                    "type": "string",
                    "description": "Absolute path to project root directory",
                },
                "scm_url": {
                    "type": "string",
                    "description": "Git remote URL (auto-detected if not provided)",
                },
                "scm_branch": {
                    "type": "string",
                    "description": "Git branch (default: main)",
                },
                "inventory": {
                    "type": "string",
                    "description": "Default inventory file relative to project root",
                },
                "default_playbook": {
                    "type": "string",
                    "description": "Default playbook filename",
                },
                "description": {
                    "type": "string",
                    "description": "Project description",
                },
                "set_default": {
                    "type": "boolean",
                    "description": "Set as the default project",
                },
            },
            "required": ["name", "path"],
        },
    ),
    Tool(
        name="unregister_project",
        description="Remove/unregister a local Ansible project from the registry. Use when user asks to 'remove project', 'unregister project', 'delete project registration'.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project alias name to remove",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="list_registered_projects",
        description="List/show all registered local Ansible projects and the default. Use this when user asks to 'list my projects', 'show registered projects', 'what projects are configured'.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="project_playbooks",
        description="Discover/find/list playbooks and roles under a registered project root. Use this when user asks to 'show project playbooks', 'find playbooks in project', 'discover playbooks', 'what playbooks does project have', 'list project roles'.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Registered project name (uses default if not specified)",
                },
                "project_path": {
                    "type": "string",
                    "description": "Direct path to scan (overrides project_name)",
                },
            },
        },
    ),
    Tool(
        name="project_run_playbook",
        description="Run a playbook using a registered project's inventory and environment. Use this when user asks to 'run project playbook', 'execute playbook from project', 'test project playbook locally'. Automatically uses the project's configured inventory.",
        inputSchema={
            "type": "object",
            "properties": {
                "playbook": {
                    "type": "string",
                    "description": "Playbook filename (relative to project root)",
                },
                "project_name": {
                    "type": "string",
                    "description": "Registered project name (uses default if not provided)",
                },
                "extra_vars": {
                    "type": "object",
                    "description": "Extra variables",
                },
                "limit": {
                    "type": "string",
                    "description": "Host limit pattern",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to run",
                },
                "skip_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to skip",
                },
                "check_mode": {
                    "type": "boolean",
                    "description": "Dry-run mode (--check)",
                },
                "verbose": {
                    "type": "number",
                    "description": "Verbosity level 0-4",
                },
            },
            "required": ["playbook"],
        },
    ),
    Tool(
        name="git_push_project",
        description="Stage, commit, and push project changes to git remote (GitHub/GitLab). Use this when user asks to 'push to git', 'commit and push', 'push playbook changes', 'push project to github', 'publish changes'. After pushing, use awx_project_update to sync AWX.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Registered project name (uses default if not provided)",
                },
                "commit_message": {
                    "type": "string",
                    "description": "Git commit message (default: 'Update playbooks via AWX MCP')",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to push to (default: from project config)",
                },
                "add_all": {
                    "type": "boolean",
                    "description": "Stage all changes with git add -A (default: true)",
                },
            },
        },
    ),
]


# ── Project Registry Tool Handlers ──
async def _h_register_project(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    reg_result = project_registry.register_project(
        name=arguments["name"],
        path=arguments["path"],
        scm_url=arguments.get("scm_url"),
        scm_branch=arguments.get("scm_branch"),
        inventory=arguments.get("inventory"),
        default_playbook=arguments.get("default_playbook"),
        description=arguments.get("description"),
        set_default=arguments.get("set_default", False),
    )
    if reg_result["status"] == "registered":
        proj = reg_result["project"]
        result = f"✅ Project registered: {proj['name']}\n"
        result += f"Path: {proj['path']}\n"
        if proj.get("scm_url"):
            result += f"SCM: {proj['scm_url']} ({proj['scm_branch']})\n"
        if proj.get("inventory"):
            result += f"Inventory: {proj['inventory']}\n"
        if proj.get("default_playbook"):
            result += f"Default playbook: {proj['default_playbook']}\n"
        if reg_result.get("is_default"):
            result += "⭐ Set as default project\n"
    else:
        result = f"❌ {reg_result['message']}"
    return [TextContent(type="text", text=result)]


async def _h_unregister_project(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    unreg_result = project_registry.unregister_project(
        name=arguments["name"],
    )
    if unreg_result["status"] == "removed":
        result = f"✅ Project '{unreg_result['project']}' removed from registry"
    else:
        result = f"❌ {unreg_result['message']}"
    return [TextContent(type="text", text=result)]


async def _h_list_registered_projects(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    proj_result = project_registry.list_projects()
    result = f"Registered Projects ({proj_result['count']}):\n\n"
    for proj in proj_result["projects"]:
        default_marker = " ⭐" if proj.get("is_default") else ""
        exists_marker = "" if proj.get("exists") else " ⚠️ (path not found)"
        result += f"📂 {proj['name']}{default_marker}{exists_marker}\n"
        result += f"   Path: {proj['path']}\n"
        if proj.get("scm_url"):
            result += f"   SCM: {proj['scm_url']} ({proj.get('scm_branch', 'main')})\n"
        if proj.get("inventory"):
            result += f"   Inventory: {proj['inventory']}\n"
        result += f"   Playbooks: {proj.get('playbook_count', 0)}\n\n"
    if not proj_result["projects"]:
        result += "  (none registered)\n"
    return [TextContent(type="text", text=result)]


async def _h_project_playbooks(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    disc_result = project_registry.discover_playbooks(
        project_name=arguments.get("project_name"),
        project_path=arguments.get("project_path"),
    )
    if disc_result.get("status") == "error":
        result = f"❌ {disc_result['message']}"
    else:
        result = f"Project: {disc_result['project_root']}\n\n"
        result += f"Playbooks ({disc_result['playbook_count']}):\n"
        for pb in disc_result["playbooks"]:
            result += f"  📄 {pb['relative_path']} ({pb['plays']} plays, hosts: {pb['hosts']})\n"
        if not disc_result["playbooks"]:
            result += "  (none found)\n"
        result += f"\nRoles ({disc_result['role_count']}):\n"
        for role in disc_result["roles"]:
            result += f"  📁 {role['name']} - {', '.join(role['directories'])}\n"
        if not disc_result["roles"]:
            result += "  (none found)\n"
    return [TextContent(type="text", text=result)]


async def _h_project_run_playbook(
    ctx: ToolContext, arguments: Any
) -> list[TextContent]:
    run_result = await project_registry.project_run_playbook(
        playbook=arguments["playbook"],
        project_name=arguments.get("project_name"),
        extra_vars=arguments.get("extra_vars"),
        limit=arguments.get("limit"),
        tags=arguments.get("tags"),
        skip_tags=arguments.get("skip_tags"),
        check_mode=arguments.get("check_mode", False),
        verbose=arguments.get("verbose", 0),
    )
    if run_result.get("status") == "error":
        result = f"❌ {run_result['message']}"
    else:
        mode = " (CHECK MODE)" if run_result.get("check_mode") else ""
        status_icon = "✅" if run_result["status"] == "successful" else "❌"
        result = (
            f"{status_icon} Project playbook execution{mode}: {run_result['status']}\n"
        )
        result += f"Project: {run_result.get('project', 'N/A')}\n"
        result += f"Playbook: {run_result['playbook']}\n\n"
        result += f"Output:\n{run_result['stdout']}"
        if run_result.get("stderr"):
            result += f"\n\nStderr:\n{run_result['stderr']}"
    return [TextContent(type="text", text=result)]


async def _h_git_push_project(ctx: ToolContext, arguments: Any) -> list[TextContent]:
    push_result = await project_registry.git_push_project(
        project_name=arguments.get("project_name"),
        commit_message=arguments.get("commit_message"),
        branch=arguments.get("branch"),
        add_all=arguments.get("add_all", True),
    )
    if push_result["status"] == "pushed":
        result = "✅ Changes pushed to git!\n"
        result += f"Project: {push_result['project']}\n"
        result += f"Branch: {push_result['branch']}\n"
        result += f"Commit: {push_result['message']}\n\n"
        result += push_result["output"]
        result += (
            "\n\n💡 Next: Use 'awx_project_update' to sync AWX with the latest changes."
        )
    elif push_result["status"] == "no_changes":
        result = f"ℹ️ {push_result['message']}"
    else:
        result = f"❌ {push_result['message']}"
    return [TextContent(type="text", text=result)]


def register(ctx: ToolContext) -> dict[str, Any]:
    """Bind this module's handlers to the server context."""
    return {
        "register_project": partial(_h_register_project, ctx),
        "unregister_project": partial(_h_unregister_project, ctx),
        "list_registered_projects": partial(_h_list_registered_projects, ctx),
        "project_playbooks": partial(_h_project_playbooks, ctx),
        "project_run_playbook": partial(_h_project_run_playbook, ctx),
        "git_push_project": partial(_h_git_push_project, ctx),
    }
