"""Core domain models for AWX MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class PlatformType(str, Enum):
    """Automation platform type."""

    AWX = "awx"  # Open source AWX
    AAP = "aap"  # Ansible Automation Platform (Red Hat)
    TOWER = "tower"  # Legacy Ansible Tower (now AAP)


class JobStatus(str, Enum):
    """AWX job status."""

    PENDING = "pending"
    WAITING = "waiting"
    RUNNING = "running"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    ERROR = "error"
    CANCELED = "canceled"


class FailureCategory(str, Enum):
    """Classification of job failure root causes."""

    INVENTORY_ISSUE = "inventory_issue"
    AUTH_FAILURE = "auth_failure"
    MISSING_VARIABLE = "missing_variable"
    SYNTAX_ERROR = "syntax_error"
    MODULE_FAILURE = "module_failure"
    CONNECTION_TIMEOUT = "connection_timeout"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


class EnvironmentConfig(BaseModel):
    """Environment configuration for AWX/AAP/Tower (no secrets)."""

    env_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    base_url: HttpUrl
    platform_type: PlatformType = (
        PlatformType.AWX
    )  # Default to AWX for backward compatibility
    verify_ssl: bool = True
    is_default: bool = False

    # Optional defaults
    default_organization: str | None = None
    default_project: str | None = None
    default_inventory: str | None = None

    # Allowlists
    allowed_job_templates: list[str] = Field(default_factory=list)
    allowed_inventories: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate environment name."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Name must be alphanumeric with hyphens/underscores only")
        return v

    class Config:
        """Pydantic config."""

        json_encoders: ClassVar[dict] = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class CredentialType(str, Enum):
    """Type of credential."""

    PASSWORD = "password"
    TOKEN = "token"


class JobTemplate(BaseModel):
    """AWX job template."""

    id: int
    name: str
    description: str | None = None
    job_type: str
    inventory: int | None = None
    project: int
    playbook: str
    extra_vars: dict[str, Any] = Field(default_factory=dict)


class Project(BaseModel):
    """AWX project."""

    id: int
    name: str
    description: str | None = None
    scm_type: str | None = None
    scm_url: str | None = None
    scm_branch: str | None = None
    status: str | None = None


class Inventory(BaseModel):
    """AWX inventory."""

    id: int
    name: str
    description: str | None = None
    organization: int | None = None
    total_hosts: int = 0
    hosts_with_active_failures: int = 0


class Job(BaseModel):
    """AWX job."""

    id: int
    name: str
    status: JobStatus
    job_template: int | None = None
    inventory: int | None = None
    project: int | None = None
    playbook: str
    extra_vars: dict[str, Any] = Field(default_factory=dict)
    started: datetime | None = None
    finished: datetime | None = None
    elapsed: float | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)


class WorkflowJobTemplate(BaseModel):
    """AWX workflow job template."""

    id: int
    name: str
    description: str | None = None
    organization: int | None = None
    inventory: int | None = None
    limit: str | None = None
    extra_vars: dict[str, Any] = Field(default_factory=dict)
    survey_enabled: bool = False
    allow_simultaneous: bool = False
    ask_variables_on_launch: bool = False
    ask_inventory_on_launch: bool = False
    ask_limit_on_launch: bool = False
    ask_tags_on_launch: bool = False
    ask_skip_tags_on_launch: bool = False
    status: str | None = None
    last_job_run: datetime | None = None
    next_job_run: datetime | None = None


class WorkflowJob(BaseModel):
    """AWX workflow job."""

    id: int
    name: str
    description: str | None = None
    status: JobStatus
    workflow_job_template: int | None = None
    inventory: int | None = None
    limit: str | None = None
    extra_vars: dict[str, Any] = Field(default_factory=dict)
    started: datetime | None = None
    finished: datetime | None = None
    elapsed: float | None = None
    failed: bool = False
    launch_type: str | None = None
    job_explanation: str | None = None


class WorkflowJobNode(BaseModel):
    """AWX workflow job node (individual step in a workflow run)."""

    id: int
    job: int | None = None
    workflow_job: int
    unified_job_template: int | None = None
    identifier: str | None = None
    do_not_run: bool = False
    success_nodes: list[int] = Field(default_factory=list)
    failure_nodes: list[int] = Field(default_factory=list)
    always_nodes: list[int] = Field(default_factory=list)
    all_parents_must_converge: bool = False
    summary_fields: dict[str, Any] = Field(default_factory=dict)


class JobEvent(BaseModel):
    """AWX job event."""

    id: int
    event: str
    event_level: int
    failed: bool
    changed: bool
    task: str | None = None
    play: str | None = None
    role: str | None = None
    host: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    event_data: dict[str, Any] = Field(default_factory=dict)


class FailureAnalysis(BaseModel):
    """Analysis of job failure."""

    job_id: int
    category: FailureCategory
    task_name: str | None = None
    play_name: str | None = None
    role_name: str | None = None
    file_path: str | None = None
    host: str | None = None
    error_message: str | None = None
    stderr: str | None = None
    suggested_fixes: list[str] = Field(default_factory=list)
    failed_events_count: int = 0


class AuditLog(BaseModel):
    """Audit log entry."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    environment: str
    user: str
    action: str
    job_template: str | None = None
    job_id: int | None = None
    success: bool
    error: str | None = None
