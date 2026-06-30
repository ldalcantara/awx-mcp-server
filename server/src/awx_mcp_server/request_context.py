"""Request-scoped AWX configuration override.

The HTTP server lets a client pass per-request AWX settings via ``X-AWX-*``
headers. These must NOT be written into the process-global ``os.environ`` —
in an async multi-request server that leaks one caller's credentials/URL into
another in-flight request. Instead we stash them in a ``ContextVar``, which is
task-local (each request/asyncio task sees only its own value).
"""

from contextvars import ContextVar, Token
from typing import Optional

_awx_override: ContextVar[Optional[dict]] = ContextVar(
    "awx_request_override", default=None
)


def set_awx_override(config: Optional[dict]) -> Token:
    """Set the per-request AWX override; returns a token for reset()."""
    return _awx_override.set(config or None)


def get_awx_override() -> dict:
    """Return the current task's AWX override (empty dict if none)."""
    return _awx_override.get() or {}


def reset_awx_override(token: Token) -> None:
    """Restore the previous override value for this task."""
    _awx_override.reset(token)
