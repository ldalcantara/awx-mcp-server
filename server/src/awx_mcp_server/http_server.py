"""HTTP server implementation for remote MCP access with monitoring."""

import asyncio
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional, AsyncIterator, cast
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response
from mcp.server import Server
from pydantic import BaseModel

from prometheus_client import CONTENT_TYPE_LATEST
from awx_mcp_server import __version__
from awx_mcp_server.monitoring import (
    monitoring_service,
    RequestTimer,
)

# Import local components
from awx_mcp_server.request_context import (
    set_awx_override,
    reset_awx_override,
)
from awx_mcp_server.utils import configure_logging, get_logger, redact_sensitive

logger = get_logger(__name__)

# API Key storage (in production, use database or Redis)
API_KEYS: dict[str, dict[str, Any]] = {}


def _truthy(val: Optional[str]) -> bool:
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}


def _anonymous_allowed() -> bool:
    """Keyless MCP access is opt-in only (default deny), so the tool-executing
    /mcp endpoint is not exposed to the network without authentication."""
    return _truthy(os.environ.get("MCP_ALLOW_ANONYMOUS"))


def _require_admin(authorization: Optional[str]) -> None:
    """Gate admin endpoints on the ADMIN_TOKEN env var. Fail closed when it is
    not configured, and compare in constant time."""
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(
            status_code=503,
            detail="Admin API is disabled: ADMIN_TOKEN is not configured.",
        )
    expected = f"Bearer {admin_token}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")


def _validate_awx_base_url(url: Optional[str]) -> None:
    """SSRF guard: only honor a client-supplied AWX base URL if its host is
    explicitly allowlisted via AWX_ALLOWED_HOSTS (comma-separated). Fail closed
    so an attacker can't point the server at internal/metadata endpoints."""
    if not url:
        return
    allowed = [
        h.strip()
        for h in os.environ.get("AWX_ALLOWED_HOSTS", "").split(",")
        if h.strip()
    ]
    host = urlparse(url).hostname or ""
    if not allowed or host not in allowed:
        raise HTTPException(
            status_code=403,
            detail=(
                "Client-supplied AWX base URL is not permitted. Set "
                "AWX_ALLOWED_HOSTS to allow specific hosts."
            ),
        )


class APIKeyCreate(BaseModel):
    """API key creation request."""

    name: str
    tenant_id: str
    expires_days: Optional[int] = 90


class APIKeyResponse(BaseModel):
    """API key response."""

    api_key: str
    name: str
    tenant_id: str
    created_at: str
    expires_at: Optional[str]


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> dict[str, Any]:
    """Verify API key and return tenant info.

    A missing or unknown key both yield 401 (not 422), so authenticated
    endpoints reject unauthenticated callers consistently.
    """
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    key_info = API_KEYS[x_api_key]

    # Check expiration
    if key_info.get("expires_at"):
        expires_at = datetime.fromisoformat(key_info["expires_at"])
        if datetime.utcnow() > expires_at:
            raise HTTPException(status_code=401, detail="API key expired")

    return key_info


def verify_api_key_optional(x_api_key: Optional[str] = Header(None)) -> dict[str, Any]:
    """
    Optional API key verification for MCP endpoints.
    If no API key provided, uses default/anonymous tenant.
    For enterprise deployments, make this required.
    """
    if x_api_key:
        if x_api_key in API_KEYS:
            key_info = API_KEYS[x_api_key]
            # Check expiration
            if key_info.get("expires_at"):
                expires_at = datetime.fromisoformat(key_info["expires_at"])
                if datetime.utcnow() > expires_at:
                    raise HTTPException(status_code=401, detail="API key expired")
            return key_info
        else:
            # API key provided but invalid
            raise HTTPException(status_code=401, detail="Invalid API key")

    # No API key provided. Anonymous access is opt-in only (default deny) so
    # the /mcp endpoint, which can execute tools, is not open to the network.
    if not _anonymous_allowed():
        raise HTTPException(
            status_code=401,
            detail=(
                "API key required. Set MCP_ALLOW_ANONYMOUS=true to permit "
                "keyless access."
            ),
        )
    return {
        "tenant_id": "default",
        "name": "Anonymous User",
        "created_at": datetime.utcnow().isoformat(),
    }


def extract_awx_config_from_headers(request: Request) -> dict[str, str]:
    """
    Extract AWX configuration from HTTP headers.
    Allows clients to pass AWX credentials per-request.
    """
    headers = request.headers
    config = {}

    if "X-AWX-Base-URL" in headers:
        config["AWX_BASE_URL"] = headers["X-AWX-Base-URL"]
    if "X-AWX-Token" in headers:
        config["AWX_TOKEN"] = headers["X-AWX-Token"]
    if "X-AWX-Username" in headers:
        config["AWX_USERNAME"] = headers["X-AWX-Username"]
    if "X-AWX-Password" in headers:
        config["AWX_PASSWORD"] = headers["X-AWX-Password"]
    if "X-AWX-Platform" in headers:
        config["AWX_PLATFORM"] = headers["X-AWX-Platform"]
    if "X-AWX-Verify-SSL" in headers:
        config["AWX_VERIFY_SSL"] = headers["X-AWX-Verify-SSL"]

    return config


async def process_mcp_message(
    mcp_server: Server, message: dict, tenant_id: str
) -> dict:
    """
    Process an MCP JSON-RPC message and return the result.
    Handles: initialize, tools/list, tools/call, resources/list, etc.
    """
    method = message.get("method")
    params = message.get("params", {})
    msg_id = message.get("id")

    try:
        # Handle different MCP methods
        if method == "initialize":
            # MCP handshake - return server info
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "awx-mcp-server",
                    "version": __version__,
                },
            }

        elif method == "tools/list":
            # List available tools - call the server's handler using class type as key
            from mcp.types import ListToolsRequest, ListToolsResult

            request = ListToolsRequest(method="tools/list", params=params)
            handler = mcp_server.request_handlers[ListToolsRequest]
            server_result = await handler(request)
            # ServerResult is a Pydantic RootModel; for a ListToolsRequest the
            # wrapped result is always a ListToolsResult.
            tools_result = cast(ListToolsResult, server_result.root)
            result = {"tools": [tool.model_dump() for tool in tools_result.tools]}

        elif method == "tools/call":
            # Call a specific tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            # Redact credential inputs / extra_vars etc. before logging.
            logger.info(
                "tool_call",
                tenant_id=tenant_id,
                tool=tool_name,
                args=redact_sensitive(tool_args),
            )

            # Create proper MCP request using class type as key
            from mcp.types import CallToolRequest, CallToolResult

            request = CallToolRequest(
                method="tools/call", params={"name": tool_name, "arguments": tool_args}
            )

            # Execute the tool through MCP server
            handler = mcp_server.request_handlers[CallToolRequest]
            server_result = await handler(request)
            # ServerResult is a Pydantic RootModel; for a CallToolRequest the
            # wrapped result is always a CallToolResult.
            tool_result = cast(CallToolResult, server_result.root)

            # Convert result to JSON-serializable format
            result = {
                "content": [
                    {
                        "type": content.type,
                        "text": (
                            content.text if hasattr(content, "text") else str(content)
                        ),
                    }
                    for content in tool_result.content
                ]
            }

        elif method == "resources/list":
            # List available resources using class type as key
            from mcp.types import ListResourcesRequest

            request = ListResourcesRequest(method="resources/list", params=params)
            handler = mcp_server.request_handlers[ListResourcesRequest]
            server_result = await handler(request)
            # ServerResult is a Pydantic RootModel - access the wrapped result via .root
            resources_result = server_result.root
            result = {
                "resources": [res.model_dump() for res in resources_result.resources]
            }

        elif method == "ping":
            # Ping/pong for keep-alive
            from mcp.types import PingRequest

            request = PingRequest(method="ping", params=params)
            handler = mcp_server.request_handlers[PingRequest]
            await handler(request)
            result = {}  # Ping returns empty result

        else:
            # Unknown method
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

        # Return successful result
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        }

    except Exception as e:
        logger.error(
            "process_mcp_message_error",
            method=method,
            error=str(e),
            tenant_id=tenant_id,
        )
        import traceback

        traceback.print_exc()
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}",
            },
        }


def create_app(mcp_server: Server) -> FastAPI:
    """Create FastAPI application with MCP server and monitoring."""
    # API docs expose the full surface; keep them off unless explicitly enabled.
    _docs_enabled = _truthy(os.environ.get("MCP_ENABLE_DOCS"))
    app = FastAPI(
        title="AWX MCP Server",
        description="Production-ready MCP server for AWX automation with monitoring",
        version=__version__,
        docs_url="/docs" if _docs_enabled else None,
        redoc_url="/redoc" if _docs_enabled else None,
    )

    # CORS: explicit allowlist from CORS_ORIGINS (comma-separated). Never pair a
    # wildcard with credentials. Empty -> no cross-origin access (same-origin).
    _cors_origins = [
        o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=bool(_cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Reject oversized request bodies (default 1 MiB; override MAX_REQUEST_BYTES).
    _max_body = int(os.environ.get("MAX_REQUEST_BYTES", str(1024 * 1024)))

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > _max_body:
            return JSONResponse(
                status_code=413, content={"detail": "Request body too large"}
            )
        return await call_next(request)

    @app.middleware("http")
    async def monitoring_middleware(request: Request, call_next):
        """Middleware to track all requests."""
        # Derive the tenant label only from a *valid* key — never echo a raw,
        # unvalidated header value into the metrics label set.
        raw_key = request.headers.get("X-API-Key")
        tenant_id = "anonymous"
        if raw_key and raw_key in API_KEYS:
            tenant_id = API_KEYS[raw_key].get("tenant_id", "anonymous")

        with RequestTimer(
            tenant_id=tenant_id,
            endpoint=request.url.path,
            method=request.method,
        ) as timer:
            try:
                response = await call_next(request)
                timer.status_code = response.status_code
                return response
            except Exception as e:
                timer.status_code = 500
                timer.error = str(e)
                raise

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "AWX MCP Server",
            "version": __version__,
            "status": "running",
            "transport": "http",
            "features": ["monitoring", "multi-tenant", "authentication"],
            "endpoints": {
                "mcp": "/mcp",
                "mcp_sse": "/mcp/sse",
                "health": "/health",
                "prometheus": "/prometheus-metrics",
                "api_keys": "/api/keys",
                # /docs only exists when MCP_ENABLE_DOCS is set.
                **({"docs": "/docs"} if _docs_enabled else {}),
            },
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "awx-mcp-server",
            "version": __version__,
        }

    @app.get("/prometheus-metrics")
    async def prometheus_metrics(tenant_info: dict = Depends(verify_api_key)):
        """
        Prometheus metrics endpoint (requires a valid API key).
        Returns metrics for all tenants in Prometheus exposition format.
        """
        metrics_data = monitoring_service.get_prometheus_metrics()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/keys", response_model=APIKeyResponse)
    async def create_api_key(
        key_request: APIKeyCreate,
        authorization: str = Header(...),
    ):
        """
        Create a new API key (requires admin authorization).
        In production, implement proper admin authentication.
        """
        _require_admin(authorization)

        # Generate secure API key
        api_key = f"awx_mcp_{secrets.token_urlsafe(32)}"
        created_at = datetime.utcnow()
        expires_at = (
            created_at + timedelta(days=key_request.expires_days)
            if key_request.expires_days
            else None
        )

        # Store API key
        API_KEYS[api_key] = {
            "name": key_request.name,
            "tenant_id": key_request.tenant_id,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

        logger.info(
            "api_key_created",
            tenant_id=key_request.tenant_id,
            name=key_request.name,
        )

        return APIKeyResponse(
            api_key=api_key,
            name=key_request.name,
            tenant_id=key_request.tenant_id,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat() if expires_at else None,
        )

    @app.get("/api/keys")
    async def list_api_keys(authorization: str = Header(...)):
        """List all API keys (admin only)."""
        _require_admin(authorization)

        return {
            "keys": [
                {
                    "api_key_preview": f"{key[:12]}...{key[-8:]}",
                    **info,
                }
                for key, info in API_KEYS.items()
            ]
        }

    # =============================================================================
    # MCP-over-HTTP Endpoints (VS Code, Claude Desktop, etc.)
    # =============================================================================

    @app.post("/mcp")
    async def mcp_endpoint(
        request: Request,
        tenant_info: dict = Depends(verify_api_key_optional),
    ):
        """
        Main MCP JSON-RPC endpoint for VS Code and other MCP clients.
        Handles all MCP protocol messages via HTTP POST.

        Optional API key authentication - if not provided, uses default tenant.
        AWX credentials can be passed via X-AWX-* headers.
        """
        tenant_id = tenant_info["tenant_id"]

        # Parse the body first, with its own error path: ``message`` must be
        # bound before the generic handler below references it, and malformed
        # JSON is a protocol-level parse error (-32700), not a 500.
        message: dict[str, Any] = {}
        try:
            message = await request.json()
        except Exception:
            return JSONResponse(
                status_code=200,  # JSON-RPC errors use 200 with error in body
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error: request body is not valid JSON",
                    },
                },
            )

        try:
            logger.info(
                "mcp_message_received",
                tenant_id=tenant_id,
                method=message.get("method"),
            )

            # Extract AWX config from headers (allows per-request credentials).
            awx_config = extract_awx_config_from_headers(request)
            # SSRF guard: only honor a client-supplied base URL if allowlisted.
            _validate_awx_base_url(awx_config.get("AWX_BASE_URL"))

            # Stash the override in a task-local ContextVar (NOT os.environ),
            # so concurrent requests can't read each other's credentials.
            ctx_token = set_awx_override(awx_config)

            try:
                # Process MCP message through the server
                # The mcp_server handles: initialize, tools/list, tools/call, resources/list, etc.
                result = await process_mcp_message(mcp_server, message, tenant_id)

                # Record metrics only after the outcome is known, so the
                # success/error split in Prometheus reflects reality.
                if message.get("method") == "tools/call":
                    tool_name = message.get("params", {}).get("name")
                    monitoring_service.record_tool_call(
                        tenant_id, tool_name, success="error" not in result
                    )

                return result

            finally:
                reset_awx_override(ctx_token)

        except HTTPException:
            # Auth / SSRF-guard rejections must surface as real HTTP errors,
            # not be wrapped into a 200 JSON-RPC error body.
            raise
        except Exception as e:
            logger.error("mcp_error", error=str(e), tenant_id=tenant_id)
            if message.get("method") == "tools/call":
                tool_name = message.get("params", {}).get("name")
                monitoring_service.record_tool_call(tenant_id, tool_name, success=False)

            # Return JSON-RPC error
            return JSONResponse(
                status_code=200,  # JSON-RPC errors use 200 with error in body
                content={
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32603,
                        "message": str(e),
                    },
                },
            )

    @app.get("/mcp/sse")
    async def mcp_sse_endpoint(
        request: Request,
        tenant_info: dict = Depends(verify_api_key_optional),
    ):
        """
        MCP Server-Sent Events endpoint for streaming responses.
        Used by some MCP clients for real-time updates.
        """
        tenant_id = tenant_info["tenant_id"]

        async def event_stream() -> AsyncIterator[str]:
            """Generate SSE events."""
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'tenant_id': tenant_id})}\n\n"

            # Keep connection alive with periodic heartbeat
            try:
                while True:
                    await asyncio.sleep(30)
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
            except asyncio.CancelledError:
                logger.info("sse_connection_closed", tenant_id=tenant_id)
                raise

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    # CORS preflight for /mcp and /mcp/sse is handled by CORSMiddleware against
    # the CORS_ORIGINS allowlist (no wildcard). A manual handler that returned
    # "Access-Control-Allow-Origin: *" was removed.

    # =============================================================================

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    return app


async def start_http_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    debug: bool = False,
):
    """Start the HTTP server with monitoring."""
    configure_logging(debug=debug)

    # Import MCP server
    try:
        from awx_mcp_server.mcp_server import create_mcp_server

        mcp_server = create_mcp_server()
    except ImportError:
        logger.warning("Could not import MCP server, using basic server")
        from mcp.server import Server

        mcp_server = Server("awx-mcp-server")

    app = create_app(mcp_server)

    logger.info("starting_http_server", host=host, port=port)

    # Use uvicorn
    import uvicorn

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="debug" if debug else "info",
        access_log=True,
    )

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    """Entry point for running as a module."""
    import argparse

    parser = argparse.ArgumentParser(description="AWX MCP HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    asyncio.run(start_http_server(host=args.host, port=args.port, debug=args.debug))
