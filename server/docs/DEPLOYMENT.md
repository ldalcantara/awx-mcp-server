# Deployment Guide

The single source of truth for deploying the AWX MCP Server. It covers the two
deployment modes, the two kinds of credentials involved, and concrete steps for
local (stdio), Docker Compose, Kubernetes/Helm, and systemd — plus a full
environment-variable reference.

For deeper topics see: [Production readiness](./PRODUCTION_READINESS.md) ·
[Multi-environment setup](./MULTI_ENVIRONMENT_SETUP.md) ·
[Logging](./LOGGING.md) · [Remote client setup](../REMOTE_CLIENT_SETUP.md) ·
[Vault integration (planned)](../VAULT_INTEGRATION.md) ·
[Install from source](../../INSTALL_FROM_SOURCE.md).

---

## 1. Choose a mode

| | **Local (stdio)** | **Remote (HTTP)** |
|---|---|---|
| Transport | stdio | HTTP + SSE |
| Who | a single developer in an editor | a shared team/enterprise service |
| Auth to the server | none (local process) | `X-API-Key` (default-deny) |
| AWX credentials | your env vars / editor secrets | per-request headers or server config |
| Start with | `awx-mcp-server` (no subcommand → stdio) | `awx-mcp-server start --host 0.0.0.0 --port 8000` |

Both modes run the same package; only the transport and auth differ.

## 2. The two credentials (don't confuse them)

- **AWX/AAP token (or username+password)** — *your* credentials to the AWX API.
  Supplied via `AWX_TOKEN` (or `AWX_USERNAME`+`AWX_PASSWORD`), or per-request
  `X-AWX-Token` / `X-AWX-*` headers on the HTTP transport.
- **MCP API key** — controls access *to this server* over HTTP. Clients send it
  as `X-API-Key`; admins mint keys against the server's `ADMIN_TOKEN`. Not used
  in local stdio mode.

## 3. Install

```bash
pip install awx-mcp-server          # from PyPI
awx-mcp-server --version
```

From source: see [INSTALL_FROM_SOURCE.md](../../INSTALL_FROM_SOURCE.md).

## 4. Local mode (stdio)

Run the server on stdio and point your MCP client (e.g. VS Code / Copilot) at
it. Provide your AWX connection via environment variables:

```bash
export AWX_BASE_URL="https://awx.example.com"
export AWX_TOKEN="<your-awx-api-token>"      # or AWX_USERNAME + AWX_PASSWORD
export AWX_VERIFY_SSL="true"
awx-mcp-server                                # stdio transport
```

Example VS Code MCP server entry:

```json
{
  "servers": {
    "awx": {
      "command": "awx-mcp-server",
      "env": { "AWX_BASE_URL": "https://awx.example.com", "AWX_TOKEN": "..." }
    }
  }
}
```

## 5. Remote mode (HTTP)

```bash
export ADMIN_TOKEN="<strong-random-secret>"   # required to mint API keys
awx-mcp-server start --host 0.0.0.0 --port 8000
```

- The tool-executing `/mcp` endpoint is **default-deny**: clients must send a
  valid `X-API-Key`. Set `MCP_ALLOW_ANONYMOUS=true` only for a trusted network.
- Mint client keys against `ADMIN_TOKEN` via the admin API (`/api/keys`).
- Clients pass their AWX credentials per request with `X-AWX-*` headers, or you
  configure a server-side AWX target via `AWX_BASE_URL`/`AWX_TOKEN`.
- If you accept a client-supplied `X-AWX-Base-URL`, you must allowlist it with
  `AWX_ALLOWED_HOSTS` (scheme+host+port) — otherwise it is rejected (SSRF guard).
- Health probe: `GET /health`. MCP: `POST /mcp`, SSE at `GET /mcp/sse`.

Front it with TLS — see the reference `deployment/nginx.conf` (TLS 1.2/1.3,
HSTS, CSP, rate limits, `/mcp/sse` long-timeout location). Detailed client-side
wiring is in [REMOTE_CLIENT_SETUP.md](../REMOTE_CLIENT_SETUP.md).

## 6. Docker Compose

`server/docker-compose.yml` builds the server plus optional Prometheus/Grafana:

```bash
cd server
export ADMIN_TOKEN="<strong-random-secret>"
docker compose up -d
docker compose ps
curl -f http://localhost:8000/health
```

The image is multi-stage and runs as a non-root user; its healthcheck calls
`/health` with `raise_for_status()`.

## 7. Kubernetes

### Raw manifest
`server/deployment/kubernetes.yaml` (namespace `awx-mcp`) ships a Deployment
(2 replicas, non-root + seccomp `RuntimeDefault`, `/health` probes), Service,
and Ingress (`ingressClassName: nginx`). Set the AWX target in the ConfigMap
(`AWX_BASE_URL`, `AWX_VERIFY_SSL`, `AWX_PLATFORM`) and the secrets
(`admin-token`, and `awx-token` **or** `awx-password`) before applying:

```bash
kubectl apply -f server/deployment/kubernetes.yaml
kubectl -n awx-mcp rollout status deploy/awx-mcp-server
```

### Helm
`server/deployment/helm` — set the AWX connection and secrets at install time:

```bash
helm install awx-mcp server/deployment/helm \
  --set config.awx.baseUrl="https://awx.example.com" \
  --set secrets.adminToken="<strong-random-secret>" \
  --set secrets.awxToken="<your-awx-api-token>"
```

The chart has a strong `securityContext` (runAsNonRoot, readOnlyRootFilesystem,
drop ALL caps, seccomp RuntimeDefault), a PodDisruptionBudget, an optional
ServiceMonitor (`prometheus.serviceMonitor.enabled`), and defaults the image tag
to the chart `appVersion` (never `latest`). If `config.awx.username` is set the
chart wires password auth (`awx-password`); otherwise it wires `awx-token`.

## 8. systemd

`server/deployment/awx-mcp-server.service` runs the installed console script as
the `awxmcp` user. Put `AWX_*` and `ADMIN_TOKEN` in
`/etc/awx-mcp-server/awx-mcp-server.env` (referenced via `EnvironmentFile=-`):

```bash
sudo cp server/deployment/awx-mcp-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now awx-mcp-server
```

## 9. Environment reference

| Variable | Mode | Purpose |
|---|---|---|
| `AWX_BASE_URL` | both | AWX/Tower/AAP base URL |
| `AWX_TOKEN` | both | AWX OAuth2 token (preferred) |
| `AWX_USERNAME` / `AWX_PASSWORD` | both | password auth (alternative to token) |
| `AWX_VERIFY_SSL` | both | verify AWX TLS cert (default `true`) |
| `AWX_PLATFORM` | both | `awx` or `aap` (default `awx`) |
| `ADMIN_TOKEN` | remote | bearer secret gating the API-key admin endpoints (fail-closed) |
| `MCP_ALLOW_ANONYMOUS` | remote | allow keyless `/mcp` access (default off) |
| `AWX_ALLOWED_HOSTS` | remote | allowlist for client-supplied `X-AWX-Base-URL` (SSRF guard) |
| `CORS_ORIGINS` | remote | comma-separated CORS allowlist (no wildcard-with-credentials) |
| `MAX_REQUEST_BYTES` | remote | request body cap (default 1 MiB) |
| `SERVER_HOST` / `SERVER_PORT` | remote | bind address/port |
| `LOG_LEVEL` | both | log verbosity |

Per-request HTTP header overrides (remote mode): `X-AWX-Base-URL`,
`X-AWX-Token`, `X-AWX-Username`, `X-AWX-Password`, `X-AWX-Platform`,
`X-AWX-Verify-SSL`.

Before going to production, work through the
[production-readiness checklist](./PRODUCTION_READINESS.md).
