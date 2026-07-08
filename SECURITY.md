# Security Policy

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue for a
suspected vulnerability.

- Use GitHub's [private vulnerability reporting](https://github.com/ldalcantara/awx-mcp-server/security/advisories/new)
  (Security → Report a vulnerability), or
- open a minimal issue asking for a private contact channel without disclosing
  details.

Please include affected version, reproduction steps, and impact. Expect an
initial acknowledgement within a few business days.

## Supported versions

Fixes land on `main` and the latest released `1.3.x`. Older versions are not
maintained.

## Security model — what to know before deploying

- **Authenticate the HTTP transport.** The tool-executing `/mcp` endpoint is
  **default-deny**: it requires an `X-API-Key` unless `MCP_ALLOW_ANONYMOUS=true`
  is explicitly set. Do not enable anonymous access on an untrusted network.
- **Admin API.** `/api/keys` requires the `ADMIN_TOKEN` bearer and fails closed
  when it is unset. Set a strong `ADMIN_TOKEN`.
- **Per-tenant isolation.** Each authenticated tenant resolves its own stored
  AWX credentials; API keys are compared in constant time.
- **SSRF guard.** A client-supplied AWX base URL (`X-AWX-Base-URL`) is only
  honored when it matches the `AWX_ALLOWED_HOSTS` allowlist (scheme + host +
  port). Leave it unset to forbid client-supplied targets entirely.
- **TLS to AWX.** `AWX_VERIFY_SSL` defaults to `true`. Disable only for trusted
  lab environments; never expose that toggle to untrusted clients.
- **Secrets.** AWX tokens/passwords and tool arguments are redacted from logs.
  Provide credentials via environment variables or an orchestrator secret
  store (Kubernetes Secret, systemd `EnvironmentFile`), never committed to the
  repo.
- **Front with TLS.** Terminate TLS at the bundled nginx config or your ingress;
  the app speaks plain HTTP behind it.
