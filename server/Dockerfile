# ---- build stage: compile wheels with the toolchain, keep it out of runtime ----
FROM python:3.11-slim-bookworm AS build

WORKDIR /app

# gcc is only needed to build any C-extension wheels; it stays in this stage.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY server/pyproject.toml server/README.md /app/server/
COPY server/src/ /app/server/src/

# Build wheels for the package and all its deps into /wheels.
RUN pip wheel --no-cache-dir --wheel-dir /wheels /app/server/

# ---- runtime stage: slim image, no compiler ----
FROM python:3.11-slim-bookworm AS runtime

LABEL org.opencontainers.image.source="https://github.com/ldalcantara/awx-mcp-server"
LABEL org.opencontainers.image.description="AWX MCP Server"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install from the prebuilt wheels only (no build tools, no network resolve).
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels awx-mcp-server \
    && rm -rf /wheels

# Create non-root user
RUN useradd -m -u 1000 awxmcp && chown -R awxmcp:awxmcp /app
USER awxmcp

EXPOSE 8000

# Health check: raise_for_status() so a 5xx is treated as unhealthy, not just
# a connection failure.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

CMD ["awx-mcp-server", "start", "--host", "0.0.0.0", "--port", "8000"]
