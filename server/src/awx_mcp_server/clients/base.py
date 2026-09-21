"""Base AWX client interface."""

import json
from abc import ABC, abstractmethod
from typing import Any

from awx_mcp_server.domain import (
    Inventory,
    Job,
    JobEvent,
    JobTemplate,
    Project,
    WorkflowJob,
    WorkflowJobNode,
    WorkflowJobTemplate,
)


class AWXClient(ABC):
    """Abstract base class for AWX clients."""

    @staticmethod
    def _parse_extra_vars(extra_vars: Any) -> dict[str, Any]:
        """Normalize AWX's ``extra_vars`` (a dict, a JSON string, or empty) to a
        dict, so callers always see the same shape."""
        if isinstance(extra_vars, dict):
            return extra_vars
        if isinstance(extra_vars, str) and extra_vars.strip():
            try:
                return json.loads(extra_vars)
            except json.JSONDecodeError:
                return {}
        return {}

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to AWX.

        Returns:
            True if connection successful
        """

    @abstractmethod
    async def list_job_templates(
        self, name_filter: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[JobTemplate]:
        """List job templates."""

    @abstractmethod
    async def get_job_template(self, template_id: int) -> JobTemplate:
        """Get job template by ID."""

    @abstractmethod
    async def list_projects(
        self, name_filter: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[Project]:
        """List projects."""

    @abstractmethod
    async def get_project(self, project_id: int) -> Project:
        """Get project by ID."""

    @abstractmethod
    async def update_project(
        self, project_id: int, wait: bool = True
    ) -> dict[str, Any]:
        """Update project from SCM."""

    @abstractmethod
    async def list_inventories(
        self, name_filter: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[Inventory]:
        """List inventories."""

    @abstractmethod
    async def launch_job(
        self,
        template_id: int,
        extra_vars: dict[str, Any] | None = None,
        limit: str | None = None,
        tags: list[str] | None = None,
        skip_tags: list[str] | None = None,
    ) -> Job:
        """Launch job from template."""

    @abstractmethod
    async def get_job(self, job_id: int) -> Job:
        """Get job by ID."""

    @abstractmethod
    async def list_jobs(
        self,
        status: str | None = None,
        created_after: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[Job]:
        """List jobs."""

    @abstractmethod
    async def cancel_job(self, job_id: int) -> dict[str, Any]:
        """Cancel running job."""

    @abstractmethod
    async def get_job_stdout(
        self, job_id: int, format: str = "txt", tail_lines: int | None = None
    ) -> str:
        """Get job stdout."""

    @abstractmethod
    async def get_job_events(
        self,
        job_id: int,
        failed_only: bool = False,
        page: int = 1,
        page_size: int = 100,
    ) -> list[JobEvent]:
        """Get job events."""

    # Workflow Job Templates

    @abstractmethod
    async def list_workflow_job_templates(
        self, name_filter: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[WorkflowJobTemplate]:
        """List workflow job templates."""

    @abstractmethod
    async def get_workflow_job_template(self, template_id: int) -> WorkflowJobTemplate:
        """Get workflow job template by ID."""

    @abstractmethod
    async def launch_workflow_job(
        self,
        template_id: int,
        extra_vars: dict[str, Any] | None = None,
        limit: str | None = None,
        tags: list[str] | None = None,
        skip_tags: list[str] | None = None,
    ) -> WorkflowJob:
        """Launch workflow job from template."""

    @abstractmethod
    async def get_workflow_job(self, job_id: int) -> WorkflowJob:
        """Get workflow job by ID."""

    @abstractmethod
    async def list_workflow_jobs(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        workflow_template_id: int | None = None,
    ) -> list[WorkflowJob]:
        """List workflow jobs."""

    @abstractmethod
    async def cancel_workflow_job(self, job_id: int) -> dict[str, Any]:
        """Cancel running workflow job."""

    @abstractmethod
    async def get_workflow_job_nodes(
        self, job_id: int, page: int = 1, page_size: int = 100
    ) -> list[WorkflowJobNode]:
        """Get workflow job nodes (individual steps)."""
