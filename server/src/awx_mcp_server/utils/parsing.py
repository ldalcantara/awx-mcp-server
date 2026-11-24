"""Utility functions for parsing and analysis."""

import re
from typing import Any

from awx_mcp_server.domain import FailureAnalysis, FailureCategory, JobEvent


def analyze_job_failure(
    job_id: int, events: list[JobEvent], stdout: str
) -> FailureAnalysis:
    """
    Analyze job failure and provide actionable suggestions.

    Args:
        job_id: Job ID
        events: List of job events
        stdout: Job stdout

    Returns:
        Failure analysis with categorization and suggestions
    """
    failed_events = [e for e in events if e.failed]

    if not failed_events:
        return FailureAnalysis(
            job_id=job_id,
            category=FailureCategory.UNKNOWN,
            suggested_fixes=["No failed events found. Check job status for details."],
        )

    # Analyze the first failed event
    event = failed_events[0]

    # Extract error details
    error_message = event.stdout or ""
    stderr = event.stderr or ""
    event_data = event.event_data

    # Try to get more detailed error info
    if "res" in event_data:
        res = event_data["res"]
        if "msg" in res:
            error_message = res["msg"]
        if "stderr" in res:
            stderr = res["stderr"]

    # Classify failure category
    category = _classify_failure(error_message, stderr, event)

    # Generate suggestions
    suggestions = _generate_suggestions(category, error_message, stderr, event)

    return FailureAnalysis(
        job_id=job_id,
        category=category,
        task_name=event.task,
        play_name=event.play,
        role_name=event.role,
        file_path=None,  # Would need to parse from stdout
        host=event.host,
        error_message=error_message,
        stderr=stderr,
        suggested_fixes=suggestions,
        failed_events_count=len(failed_events),
    )


def _classify_failure(error_msg: str, stderr: str, event: JobEvent) -> FailureCategory:
    """Classify failure category based on error patterns."""
    combined = f"{error_msg} {stderr}".lower()

    # Check for common patterns
    if any(
        pattern in combined
        for pattern in [
            "unreachable",
            "could not resolve hostname",
            "connection refused",
        ]
    ):
        return FailureCategory.INVENTORY_ISSUE

    if any(
        pattern in combined
        for pattern in [
            "permission denied",
            "authentication failed",
            "invalid credentials",
            "unauthorized",
        ]
    ):
        return FailureCategory.AUTH_FAILURE

    if any(
        pattern in combined
        for pattern in ["undefined variable", "variable is not defined"]
    ):
        return FailureCategory.MISSING_VARIABLE

    if any(
        pattern in combined
        for pattern in [
            "syntax error",
            "yaml syntax",
            "unexpected token",
            "invalid syntax",
        ]
    ):
        return FailureCategory.SYNTAX_ERROR

    if "timeout" in combined or "timed out" in combined:
        return FailureCategory.CONNECTION_TIMEOUT

    if "permission" in combined and "denied" in combined:
        return FailureCategory.PERMISSION_DENIED

    # Check for module-specific failures
    if (
        event.task
        and any(mod in event.task.lower() for mod in ["yum", "apt", "dnf", "package"])
        and ("no package" in combined or "not found" in combined)
    ):
        return FailureCategory.MODULE_FAILURE

    return FailureCategory.UNKNOWN


def _generate_suggestions(
    category: FailureCategory, error_msg: str, stderr: str, event: JobEvent
) -> list[str]:
    """Generate actionable suggestions based on failure category."""
    suggestions = []

    if category == FailureCategory.INVENTORY_ISSUE:
        suggestions.extend(
            [
                "Verify the host exists in the inventory",
                "Check network connectivity to the target host",
                "Ensure the hostname resolves correctly (check DNS or /etc/hosts)",
                "Verify firewall rules allow SSH connections",
            ]
        )

    elif category == FailureCategory.AUTH_FAILURE:
        suggestions.extend(
            [
                "Verify SSH credentials or keys are correct",
                "Check that the user has access to the target host",
                "Ensure SSH key is in the authorized_keys file",
                "Verify sudo/become password if required",
            ]
        )

    elif category == FailureCategory.MISSING_VARIABLE:
        # Try to extract variable name
        var_match = re.search(r"['\"]([\w_]+)['\"].*undefined", error_msg + stderr)
        if var_match:
            var_name = var_match.group(1)
            suggestions.append(
                f"Define the variable '{var_name}' in extra_vars or playbook"
            )
        suggestions.extend(
            [
                "Check the playbook for required variables",
                "Add missing variables to extra_vars in the job template",
                "Verify variable names are spelled correctly",
            ]
        )

    elif category == FailureCategory.SYNTAX_ERROR:
        suggestions.extend(
            [
                "Check YAML syntax in the playbook",
                "Verify proper indentation (use spaces, not tabs)",
                "Run ansible-playbook --syntax-check locally",
                "Check for missing quotes or special characters",
            ]
        )

    elif category == FailureCategory.CONNECTION_TIMEOUT:
        suggestions.extend(
            [
                "Increase timeout values in ansible.cfg",
                "Check network latency to target hosts",
                "Verify no firewall is blocking connections",
                "Check if target host is overloaded",
            ]
        )

    elif category == FailureCategory.PERMISSION_DENIED:
        suggestions.extend(
            [
                "Check file/directory permissions on target host",
                "Verify the user has necessary privileges",
                "Use 'become: yes' if elevated privileges are needed",
                "Check SELinux/AppArmor policies if applicable",
            ]
        )

    elif category == FailureCategory.MODULE_FAILURE:
        suggestions.extend(
            [
                f"Check module '{event.task}' documentation for required parameters",
                "Verify the module is available on the target system",
                "Check module prerequisites are installed",
                "Review module error message for specific issues",
            ]
        )

    else:
        suggestions.extend(
            [
                "Review the full job output for more context",
                "Check Ansible module documentation",
                "Verify all task parameters are correct",
                "Try running the task manually on the target host",
            ]
        )

    return suggestions


# Keys whose values must never reach the logs. Matched as substrings of the
# lowercased key, so e.g. "awx_token" and "extra_vars" are both caught.
_SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "credential",
    "authorization",
    "extra_vars",  # frequently carries passwords/keys for playbooks
    "inputs",  # AWX credential inputs
)


def redact_sensitive(data: Any) -> Any:
    """Return a log-safe copy of ``data``.

    Values under keys that look sensitive (password/token/extra_vars/...) are
    replaced with ``[REDACTED]``; containers are walked recursively. Non-dict,
    non-list values pass through unchanged.
    """
    if isinstance(data, dict):
        return {
            key: (
                "[REDACTED]"
                if any(part in key.lower() for part in _SENSITIVE_KEY_PARTS)
                else redact_sensitive(value)
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact_sensitive(item) for item in data]
    return data


def sanitize_secret(text: str, secrets: list[str]) -> str:
    """
    Sanitize secrets from text.

    Args:
        text: Text that may contain secrets
        secrets: List of secret strings to redact

    Returns:
        Text with secrets replaced by [REDACTED]
    """
    result = text
    for secret in secrets:
        if secret and len(secret) > 0:
            result = result.replace(secret, "[REDACTED]")
    return result


# Launch fields a caller may pass, and the template flags that make AWX accept
# them. A variable is also accepted through a survey, for the keys the survey
# declares; that partial case is left to AWX's own ``ignored_fields``.
_LAUNCH_PROMPTS: dict[str, tuple[str, ...]] = {
    "limit": ("ask_limit_on_launch",),
    "tags": ("ask_tags_on_launch",),
    "skip_tags": ("ask_skip_tags_on_launch",),
    "extra_vars": ("ask_variables_on_launch", "survey_enabled"),
}


LAUNCH_FIELDS = tuple(_LAUNCH_PROMPTS)
LAUNCH_PROMPT_FLAGS = tuple(
    sorted({f for flags in _LAUNCH_PROMPTS.values() for f in flags})
)


def unprompted_launch_fields(
    arguments: dict[str, Any], prompts: dict[str, Any]
) -> list[str]:
    """Name the launch fields that were passed but that the template will ignore.

    AWX does not reject a launch field the template does not prompt for: it
    drops it, starts the job with the template's own value and only mentions
    the field in ``ignored_fields``. For ``limit`` that means running on the
    template's whole scope. ``prompts`` is the template's launch configuration
    (``ask_*_on_launch`` and ``survey_enabled``).
    """
    return [
        field
        for field, flags in _LAUNCH_PROMPTS.items()
        if arguments.get(field) and not any(prompts.get(f) for f in flags)
    ]


def describe_ignored_fields(ignored: dict[str, Any]) -> str:
    """Render AWX's ``ignored_fields``, e.g. ``limit, extra_vars (foo, bar)``."""
    parts = []
    for field, value in ignored.items():
        if isinstance(value, dict) and value:
            parts.append(f"{field} ({', '.join(sorted(map(str, value)))})")
        else:
            parts.append(str(field))
    return ", ".join(parts)


def launch_refusal(template_name: str, fields: list[str]) -> str:
    """Text returned instead of launching when fields would be dropped."""
    return (
        f"Not launched: template '{template_name}' does not prompt on launch for "
        f"{', '.join(fields)}. AWX would drop these fields and run with the "
        "template's own values (a dropped limit means the template's own limit, or "
        "its whole inventory if it has none). Remove them, or turn on 'Prompt on "
        "launch' for them in the template."
    )


def ignored_fields_note(ignored: Any) -> str:
    """A warning line for a launch response whose ``ignored_fields`` is not empty."""
    if not isinstance(ignored, dict) or not ignored:
        return ""
    return (
        f"\n⚠ AWX ignored: {describe_ignored_fields(ignored)}. The template does not "
        "prompt for these on launch, so the job runs with the template's own values "
        "for them.\n"
    )
