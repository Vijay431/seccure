"""Deterministic audit fan-out and Dependabot enrichment helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from src.config.config import ToolResult
from src.utils.github_issues import list_security_issues
from src.utils.github_pulls import list_dependabot_prs
from src.utils.github_security import (
    list_code_scanning_alerts,
    list_dependabot_alerts,
)


async def run_audit_fanout() -> ToolResult:
    """Run the three audit sources concurrently using subagents."""
    from src.pipelines.subagents.audit_issue_agent import build_audit_issue_agent
    from src.pipelines.subagents.audit_pr_agent import build_audit_pr_agent
    from src.pipelines.subagents.audit_security_agent import build_audit_security_agent

    # Explicit allow-lists for US1
    issue_tools: list[Callable[..., Any]] = [
        list_security_issues,
    ]
    pr_tools: list[Callable[..., Any]] = [
        list_dependabot_prs,
    ]
    security_tools: list[Callable[..., Any]] = [
        list_dependabot_alerts,
        list_code_scanning_alerts,
    ]

    issue_agent = build_audit_issue_agent(tools=issue_tools)
    pr_agent = build_audit_pr_agent(tools=pr_tools)
    security_agent = build_audit_security_agent(tools=security_tools)

    try:
        import json

        async with issue_agent as ia, pr_agent as pa, security_agent as sa:
            issue_res, pr_res, sec_res = await asyncio.gather(
                ia.chat("Begin issue audit. Return the IssueSummary."),
                pa.chat("Begin PR audit. Return the PRSummary."),
                sa.chat("Begin security audit. Return the AlertSummary."),
            )
            issue_text = await issue_res.text()
            pr_text = await pr_res.text()
            sec_text = await sec_res.text()

            data = {
                "security_issues": json.loads(issue_text),
                "dependabot_prs": json.loads(pr_text),
                "alerts": json.loads(sec_text),
            }
    except PermissionError as exc:
        return ToolResult(ok=False, fatal=True, message=str(exc))
    except Exception as exc:
        # We catch and wrap other exceptions to ensure the system handles failures gracefully
        return ToolResult(ok=False, fatal=True, message=f"Subagent failure: {exc}")

    return ToolResult(
        ok=True,
        fatal=False,
        message="audit fan-out completed",
        data=data,
        reasoning_summary="Spawned AuditIssueAgent, AuditPRAgent, and AuditSecurityAgent concurrently.",
    )
