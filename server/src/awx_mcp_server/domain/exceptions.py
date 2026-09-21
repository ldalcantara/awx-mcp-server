"""Custom exceptions for AWX MCP Server."""


class AWXMCPError(Exception):
    """Base exception for AWX MCP errors."""


class EnvironmentNotFoundError(AWXMCPError):
    """Environment not found."""


class EnvironmentAlreadyExistsError(AWXMCPError):
    """Environment already exists with this name."""


class NoActiveEnvironmentError(AWXMCPError):
    """No active environment set."""


class CredentialError(AWXMCPError):
    """Credential storage or retrieval error."""


class AWXClientError(AWXMCPError):
    """AWX client operation error."""


class AWXAuthenticationError(AWXClientError):
    """AWX authentication failed."""


class AWXConnectionError(AWXClientError):
    """Failed to connect to AWX."""


class AWXPermissionError(AWXClientError):
    """Insufficient permissions for AWX operation."""


class JobNotFoundError(AWXClientError):
    """Job not found."""


class TemplateNotFoundError(AWXClientError):
    """Job template not found."""


class ProjectNotFoundError(AWXClientError):
    """Project not found."""


class AllowlistViolationError(AWXMCPError):
    """Operation blocked by allowlist."""


class ConfigurationError(AWXMCPError):
    """Configuration error."""


class ValidationError(AWXMCPError):
    """Validation error."""
