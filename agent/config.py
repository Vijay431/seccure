"""Pydantic models for SeccureState and subagent response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class SeccureState(BaseModel):
    """Shared mutable state persisted to disk and read by all agents."""

    run_id: str
    repo: str  # "owner/repo"
    default_branch: str = "main"
    fix_branch: str = ""
    constraints: str = ""  # raw text from .seccure/constraints.md (empty = no constraints)
    alerts: list[AlertItem] = Field(default_factory=list)
    dependabot_prs: list[PRItem] = Field(default_factory=list)
    security_issues: list[IssueItem] = Field(default_factory=list)
    fix_results: list[FixResult] = Field(default_factory=list)
    conflict_issue_numbers: list[int] = Field(default_factory=list)
    closed_seccure_pr: int | None = None
    pr_number: int | None = None
    token_usage: dict[str, dict[str, int]] = Field(default_factory=dict)
    status: str = "pending"  # pending | fixing | done | nothing_to_fix | error


# ---------------------------------------------------------------------------
# Subagent response schemas (enforced via response_schema= in LocalAgentConfig)
# ---------------------------------------------------------------------------


class IssueSummary(BaseModel):
    """Structured output contract for IssueAgent."""

    items: list[IssueItem]
    count: int


class PRSummary(BaseModel):
    """Structured output contract for PRAgent."""

    items: list[PRItem]
    count: int


class AlertSummary(BaseModel):
    """Structured output contract for SecurityAgent."""

    items: list[AlertItem]
    count: int
    critical_count: int
    high_count: int


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
    COORDINATOR_MAX_TOOL_CALLS: int = int(_os.environ.get("SECCURE_COORDINATOR_MAX_TOOLS", "60"))
    SUBAGENT_MAX_TOOL_CALLS: int = int(_os.environ.get("SECCURE_SUBAGENT_MAX_TOOLS", "10"))

    # Wall-clock timeout (seconds) for the *entire* coordinator run, including
    # the time spent in subagents.  Default = 30 minutes.
    TOTAL_RUN_TIMEOUT_SECONDS: int = int(_os.environ.get("SECCURE_TIMEOUT_SECONDS", "1800"))
