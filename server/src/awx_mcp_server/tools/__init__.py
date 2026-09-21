"""Per-domain tool modules for the AWX MCP server.

Each module exposes ``TOOLS`` (its ``Tool`` schemas) and ``register(ctx)``
(name -> bound handler). ``TOOL_MODULES`` fixes the aggregation order.
"""

from awx_mcp_server.tools import (
    env,
    inventory,
    jobs,
    local_ansible,
    local_projects,
    notifications,
    projects,
    schedules,
    system,
    templates,
    workflows,
)

TOOL_MODULES = [
    env,
    system,
    templates,
    projects,
    inventory,
    jobs,
    schedules,
    workflows,
    notifications,
    local_ansible,
    local_projects,
]
