# Changelog

All notable changes to the AWX MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Schedule listings now show the **inventory override** next to the limit.
  A schedule may override the template's inventory when the template prompts
  for one, so two schedules sharing a limit name can target entirely
  different machines — showing the limit alone invites the opposite
  conclusion.
- **Schedule tools** — `awx_schedules_list`, `awx_schedule_get`,
  `awx_schedule_create`, `awx_schedule_update`, `awx_schedule_delete`, over
  `/api/v2/schedules/`. The only schedule tool until now was
  `awx_workflow_template_schedules`, which shows one workflow's slice; an
  instance whose schedules hang off job templates, project updates and
  inventory sources reported nothing scheduled at all. Listing accepts a name
  filter and a `unified_job_template` id, and every response names what the
  schedule runs, its recurrence rule, whether it is enabled and the next run.

### Fixed
- **Adopt ruff 0.16 across the whole repository.** The linter now runs the
  0.16 rule set: 325 findings auto-fixed (import order, `Optional[X]` ->
  `X | None`, `Dict` -> `dict`, redundant `pass`, f-string conversions), 12
  fixed by hand (collapsed nested `if`s, a swallowed exception now logged,
  `dict.keys()` membership, `exit` -> `sys.exit`, `ClassVar` on a Pydantic
  `Config` attribute, explicit `check=` on `subprocess.run`), and 55 unused
  `env` unpackings renamed to `_env`. Six rules are exempted in
  `[tool.ruff.lint]`, each with the reason in the file. A new root `ruff.toml`
  extends the package config, so `tests/` and the root-level scripts are
  linted under the same policy instead of ruff's bare defaults.

- **Optional tool fields were sent as `null`.** `tools/list` and
  `resources/list` serialized SDK models with a bare `model_dump()`, so every
  optional field (`title`, `icons`, `outputSchema`, `annotations`,
  `execution`, `_meta`) went on the wire as `null`. Strict clients — Claude
  Code among them — reject that and fail the whole tool listing
  (`tools.0.title: Invalid input, …`). Responses now use
  `model_dump(by_alias=True, mode="json", exclude_none=True)`, and
  `tools/call` returns the full `CallToolResult`, so `isError` and
  `structuredContent` reach the client instead of being dropped.
- **`initialize` advertised a `resources` capability the server does not
  have.** No resources handler is registered, so a client that trusted the
  capability list called `resources/list` and got `-32603 Internal error`
  (a `KeyError` on the handler table). The capability is no longer
  advertised, and `resources/list` answers with an empty list when nothing is
  registered.
- **Pin the MCP Python SDK to `<2`.** SDK 2.0 removed the 1.x low-level
  `Server.list_tools()` / `call_tool()` decorators that `mcp_server.py` uses;
  a fresh `pip install` resolved to 2.x and the server started, then crashed
  with `AttributeError: 'Server' object has no attribute 'list_tools'`. Every
  container image built from this repo since the 2.0 release was affected.
  The dependency is now `mcp>=1.0.0,<2` until the server is ported to the
  2.x API.

### Performance
- **Connection reuse across tool calls** — the server now caches one
  `CompositeAWXClient` per resolved (URL, credentials) and marks it
  `persistent`, so per-handler `async with client` blocks keep the httpx
  connection pool open. Repeated tool calls reuse warm connections instead of
  paying a fresh TCP+TLS handshake on every call. The cache holds up to 8
  clients (LRU); evicted clients are closed in the background.
- **Full listings fetch at AWX's max page size** — paginated list methods now
  request `page_size=200` when starting from page 1, so collecting all pages
  (up to the 1000-item guard) costs ~5 round-trips instead of ~40 at the
  25-item default. An explicit `page > 1` keeps the caller's `page_size`,
  preserving page offsets. Introduced `RestAWXClient._get_all()` to replace
  the request-then-`_all_results` boilerplate at every list call site.
- Hoisted per-request `get_logger()`/`import json` calls in
  `rest_client.py` to module level (they ran on every HTTP request).

### Fixed
- `/mcp` no longer crashes with an `UnboundLocalError` on a malformed JSON
  body — it now returns a proper JSON-RPC parse error (`-32700`).
- `/`, `/health`, the FastAPI app metadata, and the MCP `initialize`
  handshake now report the real package version (previously stale
  hardcoded `1.0.0` / `1.1.6` strings).
- The `awx_mcp_tool_calls_total{status}` metric now records the actual
  JSON-RPC outcome instead of unconditionally counting `success` before
  the tool ran.

### Security
- Tool-call arguments are redacted before logging (new
  `utils.redact_sensitive`): values under keys matching password / token /
  secret / credential / `extra_vars` / `inputs` etc. are masked, so
  playbook secrets and AWX credential inputs no longer land in the logs.
- Removed all SurgeX-Labs branding and hostnames from the repository:
  package metadata, MCP registry names, Docker image names and the VS Code
  publisher/extension ID now use `ldalcantara`; documentation examples use
  neutral `example.com` placeholders.

## [1.3.0] - 2026-04-24

### Added
- **Workflow Job Template support (PR #1)** — 13 new MCP tools for AWX workflows:
  - Templates: `awx_workflow_templates_list`, `awx_workflow_template_get`,
    `awx_workflow_template_nodes`, `awx_workflow_template_survey`,
    `awx_workflow_template_schedules`, `awx_workflow_template_launch_config`
  - Jobs: `awx_workflow_job_launch`, `awx_workflow_job_get`, `awx_workflow_jobs_list`,
    `awx_workflow_job_cancel`, `awx_workflow_job_nodes`, `awx_workflow_job_relaunch`,
    `awx_workflow_job_delete`
- **Notification support (PR #1)** — 13 new MCP tools:
  - Notification templates: `awx_notification_templates_list`,
    `awx_notification_template_get`, `awx_notification_template_create`,
    `awx_notification_template_update`, `awx_notification_template_delete`,
    `awx_notification_template_test`
  - History: `awx_notifications_list`
  - Job-template associations: `awx_job_template_notifications_list`,
    `awx_job_template_notification_associate`, `awx_job_template_notification_disassociate`
  - Workflow-template associations: `awx_workflow_template_notifications_list`,
    `awx_workflow_template_notification_associate`, `awx_workflow_template_notification_disassociate`
- Documentation updated for the new tools: `AWX_MCP_QUERY_REFERENCE.md`
  (new Workflow Job Templates, Workflow Jobs, and Notifications sections + Tool
  Summary Table rows) and `server/README.md`. Total tool count is now **76**.

_Contributed by Connor Griffin (`connor-griffin5`)._

## [1.2.0] - 2026-02-22

### Added
- **Production Readiness**: Comprehensive production deployment documentation
  - Production readiness checklist and feature assessment
  - Performance characteristics and benchmarks
  - High availability setup with Kubernetes examples
  - Security guidelines by environment type
  
- **Multi-Environment Support**: Complete guide for managing multiple AWX/AAP environments
  - Configuration examples for Local, Dev, Staging, and Production environments
  - Environment switching via Copilot Chat dropdown
  - Environment-specific security best practices
  - Transaction logging with environment context
  
- **Comprehensive Documentation Structure**:
  - New `/docs` folder with organized documentation
  - `MULTI_ENVIRONMENT_SETUP.md` - Multi-environment configuration guide
  - `PRODUCTION_READINESS.md` - Production deployment checklist
  - `LOGGING.md` - Logging and monitoring architecture
  - `ENDPOINT_CLEANUP.md` - API cleanup strategy and rationale
  - `docs/README.md` - Documentation index and navigation
  - `PRODUCTION_READY_SUMMARY.md` - Quick reference summary
  
- **Logging & Monitoring Enhancements**:
  - Documented structured JSON logging with all transaction details
  - Prometheus metrics integration guide
  - ELK Stack and Splunk integration examples
  - Alerting rules for production monitoring
  - Log retention policies
  
- **API Cleanup Documentation**:
  - Clear separation between production and legacy endpoints
  - Migration guide from REST API to MCP protocol
  - Rationale for endpoint consolidation (60% code reduction)

### Changed
- Enhanced README with proper documentation organization
- Improved HTTP server with cleaner endpoint structure
- Better authentication handling for multi-environment scenarios

### Documentation
- Complete restructure of documentation for production use
- Added 2500+ lines of comprehensive guides
- Professional documentation index with use-case navigation
- Quick reference guides for common scenarios

### Security
- Documented security best practices per environment type
- Token-based authentication recommendations for production
- SSL/TLS configuration guidelines
- Credential management improvements

## [1.1.6] - Previous Release

### Features
- HTTP server mode for remote MCP access
- MCP-over-HTTP with SSE support
- 49 AWX automation tools
- API key management
- Health and metrics endpoints
- Structured logging with structlog
- Prometheus metrics integration

---

For more details, see the [GitHub repository](https://github.com/ldalcantara/awx-mcp-server).
