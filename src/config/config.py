"""Pydantic models for SeccureState and subagent response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ToolResult(BaseModel):
    """Typed result envelope for deterministic tools."""

    ok: bool
    fatal: bool = False
    message: str
    data: dict[str, Any] | list[Any] | None = None
    reasoning_summary: str | None = None


class DependencyFinding(BaseModel):
    """A dependency-related finding from PRs, alerts, or issues."""

    source: Literal["dependabot_pr", "dependabot_alert", "issue"]
    package: str
    ecosystem: str
    severity: str | None = None
    cve_id: str | None = None
    patched_version: str | None = None
    advisory_url: str | None = None
    alert_number: int | None = None
    pr_number: int | None = None
    issue_number: int | None = None
    from_version: str | None = None
    to_version: str | None = None
    url: str | None = None

    @field_validator("package", "ecosystem")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class CodeScanningFinding(BaseModel):
    """A non-dependency code scanning/security finding."""

    source: Literal["code_scanning"] = "code_scanning"
    rule_id: str
    severity: str
    description: str
    url: str
    alert_number: int


class AlertItem(BaseModel):
    """A single Dependabot / code-scanning vulnerability alert."""

    cve_id: str
    package: str
    severity: str  # "low" | "medium" | "high" | "critical"
    patched_version: str | None = None
    advisory_url: str
    alert_number: int


class PRItem(BaseModel):
    """A single open Dependabot pull request."""

    pr_number: int
    package: str
    from_version: str
    to_version: str
    url: str


class IssueItem(BaseModel):
    """A single GitHub issue labelled security or dependabot."""

    issue_number: int
    title: str
    labels: list[str]
    url: str


class FixResult(BaseModel):
    """Result of an attempted package fix."""

    package: str
    fixed: bool
    strategy: str  # "npm_audit_fix" | "npm_overrides" | "manual_bump" | "unresolved"
    from_version: str
    to_version: str | None = None
    reason_if_failed: str | None = None
    cve_id: str | None = None
    severity: str | None = None


class SeccureState(BaseModel):
    """Shared mutable state persisted to disk and read by all agents."""

    run_id: str
    repo: str  # "owner/repo"
    default_branch: str = "main"
    fix_branch: str = ""
    ecosystem: str = "all"  # E.g. "npm", "python", "all"
    # Raw text from .seccure/constraints.md; empty means no constraints.
    constraints: str = ""
    alerts: list[AlertItem] = Field(default_factory=list)
    dependency_findings: list[DependencyFinding] = Field(default_factory=list)
    code_scanning_findings: list[CodeScanningFinding] = Field(default_factory=list)
    dependabot_prs: list[PRItem | DependencyFinding] = Field(default_factory=list)
    security_issues: list[IssueItem] = Field(default_factory=list)
    fix_results: list[FixResult] = Field(default_factory=list)
    conflict_issue_numbers: list[int] = Field(default_factory=list)
    closed_seccure_pr: int | None = None
    pr_number: int | None = None
    attempt_count: int = 0
    status_reason: str = ""
    errors: list[str] = Field(default_factory=list)
    agent_events_path: str = ""
    token_usage: dict[str, dict[str, int]] = Field(default_factory=dict)
    status: str = "pending"  # pending | fixing | done | nothing_to_fix | error


# ---------------------------------------------------------------------------
# Subagent response schemas (enforced through the OpenRouter response format)
# ---------------------------------------------------------------------------


class IssueSummary(BaseModel):
    """Structured output contract for IssueAgent."""

    items: list[IssueItem]
    count: int
    summarization: str
    action_required: bool


class PRSummary(BaseModel):
    """Structured output contract for PRAgent."""

    items: list[PRItem]
    count: int
    summarization: str
    action_required: bool


class AlertSummary(BaseModel):
    """Structured output contract for SecurityAgent."""

    items: list[AlertItem]
    count: int
    critical_count: int
    high_count: int
    summarization: str
    action_required: bool


# ---------------------------------------------------------------------------
# Execution guard-rails
# ---------------------------------------------------------------------------


class RunLimits:
    """Hard limits that prevent agents from running indefinitely.

    All values can be overridden with environment variables so that
    operators can tune them in CI without code changes.
    """

    import os as _os

    # Maximum number of tool calls a single agent turn is allowed to make.
    # Coordinator has more tools and a more complex task, so its ceiling is
    # intentionally higher than for the narrow data-gathering subagents.
    COORDINATOR_MAX_TOOL_CALLS: int = int(
        _os.environ.get("SECCURE_COORDINATOR_MAX_TOOLS", "60")
    )
    SUBAGENT_MAX_TOOL_CALLS: int = int(
        _os.environ.get("SECCURE_SUBAGENT_MAX_TOOLS", "10")
    )

    # Wall-clock timeout (seconds) for the *entire* coordinator run, including
    # the time spent in subagents.  Default = 30 minutes.
    TOTAL_RUN_TIMEOUT_SECONDS: int = int(
        _os.environ.get("SECCURE_TIMEOUT_SECONDS", "1800")
    )
