# Contributing

Thanks for your interest in improving awx-mcp-server.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e "./server[dev]" ruff black mypy
```

The Python package lives under `server/src/awx_mcp_server/`; tests under
`tests/`. There is also a VS Code extension under `vscode-extension/`.

## Before opening a PR

Run the same checks CI enforces:

```bash
ruff check .
black --check .
# enforced typed core (must pass):
mypy server/src/awx_mcp_server/domain server/src/awx_mcp_server/storage \
     server/src/awx_mcp_server/utils server/src/awx_mcp_server/request_context.py \
     server/src/awx_mcp_server/monitoring.py server/src/awx_mcp_server/auth.py \
     server/src/awx_mcp_server/cli.py server/src/awx_mcp_server/__main__.py \
     server/src/awx_mcp_server/__init__.py
cd tests && pytest -q
```

Guidelines:

- **Add tests** for new behavior and bug fixes. Prefer mocked unit tests (no
  live AWX); integration tests that need a real AWX are gated to the manual
  `workflow_dispatch` CI job.
- **Keep the typed core clean** — mypy is enforced on the modules listed above
  and advisory (ratcheting down) on the rest; don't add new errors to the core.
- **Don't log secrets.** Route sensitive values through the existing redaction
  helpers, and never return internal error text to clients.
- **Conventional-ish commits** (`fix:`, `feat:`, `chore:`, `docs:`) and a
  focused PR are appreciated.

## Reporting security issues

See [SECURITY.md](SECURITY.md) — please report vulnerabilities privately.
