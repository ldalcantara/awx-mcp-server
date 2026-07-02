# Changelog

All notable changes to the AWX MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
