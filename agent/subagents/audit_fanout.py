"""Deterministic audit fan-out and Dependabot enrichment helpers."""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from google.antigravity import ToolContext

from agent.config import CodeScanningFinding, DependencyFinding, ToolResult
from agent.state import write_state_section
from agent.tools.github_issues import list_security_issues
from agent.tools.github_pulls import list_dependabot_prs
from agent.tools.github_security import (
    list_code_scanning_alerts,
    list_dependabot_alerts,
)

AuditCallable = Callable[..., str | Awaitable[str]]


def infer_ecosystem_from_files(files: Iterable[str]) -> str:
    """Infer Dependabot ecosystem from changed manifest or lockfile names."""

    names = {name.rsplit("/", 1)[-1] for name in files}
    if {"package.json", "package-lock.json"} & names:
        return "npm"
    if "pnpm-lock.yaml" in names:
        return "pnpm"
    if "yarn.lock" in names:
        return "yarn"
    if {"pyproject.toml", "uv.lock", "requirements.txt"} & names:
        return "pip"
    if "go.mod" in names or "go.sum" in names:
        return "gomod"
    if "Cargo.toml" in names or "Cargo.lock" in names:
        return "cargo"
    return "unknown"


def _parse_dependabot_title(title: str) -> tuple[str, str | None, str | None]:
    match = re.search(
        r"(?:bump|update)\s+(?P<pkg>[\w@/.-]+)(?:\s+requirement)?\s+from\s+"
        r"(?P<from>[<>=^~]*[\d.\w-]+)\s+to\s+(?P<to>[<>=^~]*[\d.\w-]+)",
        title,
        re.IGNORECASE,
    )
    if match:
        return match.group("pkg"), match.group("from"), match.group("to")
    return title or "unknown", None, None


def enrich_dependabot_pr(
    pr: dict[str, Any],
    changed_files: Iterable[str] = (),
) -> DependencyFinding:
    """Create a compact dependency finding from a Dependabot PR."""

    package, from_version, to_version = _parse_dependabot_title(
        str(pr.get("title", ""))
    )
    ecosystem = infer_ecosystem_from_files(changed_files)
    if ecosystem == "unknown":
        ecosystem = str(pr.get("ecosystem") or "unknown")

    return DependencyFinding(
        source="dependabot_pr",
        package=str(pr.get("package") or package),
        ecosystem=ecosystem,
        pr_number=int(pr.get("number") or pr.get("pr_number")),
        from_version=pr.get("from_version") or from_version,
        to_version=pr.get("to_version") or to_version,
        url=pr.get("html_url") or pr.get("url"),
    )


def _as_json_list(payload: str) -> list[dict[str, Any]]:
    data = json.loads(payload)
    return data if isinstance(data, list) else []


def _dependabot_alert_to_finding(alert: dict[str, Any]) -> DependencyFinding:
    return DependencyFinding(
        source="dependabot_alert",
        package=str(alert.get("package") or "unknown"),
        ecosystem=str(alert.get("ecosystem") or "unknown"),
        severity=alert.get("severity"),
        cve_id=alert.get("cve_id"),
        patched_version=alert.get("patched_version"),
        advisory_url=alert.get("advisory_url"),
        alert_number=alert.get("alert_number"),
    )


def _code_alert_to_finding(alert: dict[str, Any]) -> CodeScanningFinding:
    return CodeScanningFinding(
        rule_id=str(alert.get("rule_id") or "unknown"),
        severity=str(alert.get("severity") or "unknown"),
        description=str(alert.get("description") or ""),
        url=str(alert.get("url") or ""),
        alert_number=int(alert.get("number") or alert.get("alert_number")),
    )


def _issue_to_item(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_number": issue.get("issue_number") or issue.get("number"),
        "title": issue.get("title") or "",
        "labels": issue.get("labels") or [],
        "url": issue.get("url") or issue.get("html_url") or "",
    }


async def _call_tool(tool: AuditCallable, *args: Any) -> str:
    result = tool(*args)
    if inspect.isawaitable(result):
        return await result
    return result


async def run_audit_fanout(
    ctx: ToolContext,
    issue_tool: AuditCallable = list_security_issues,
    pr_tool: AuditCallable = list_dependabot_prs,
    dependabot_alert_tool: AuditCallable = list_dependabot_alerts,
    code_scanning_tool: AuditCallable = list_code_scanning_alerts,
) -> ToolResult:
    """Run the three audit sources concurrently and return compact findings."""

    try:
        issues_raw, prs_raw, dep_alerts_raw, code_alerts_raw = await asyncio.gather(
            _call_tool(issue_tool, ctx),
            _call_tool(pr_tool, ctx),
            _call_tool(dependabot_alert_tool, ctx),
            _call_tool(code_scanning_tool, ctx),
        )
    except PermissionError as exc:
        return ToolResult(ok=False, fatal=True, message=str(exc))

    pr_findings = [enrich_dependabot_pr(pr) for pr in _as_json_list(prs_raw)]
    dependency_findings = pr_findings + [
        _dependabot_alert_to_finding(alert) for alert in _as_json_list(dep_alerts_raw)
    ]
    code_findings = [
        _code_alert_to_finding(alert) for alert in _as_json_list(code_alerts_raw)
    ]
    security_issues = [_issue_to_item(issue) for issue in _as_json_list(issues_raw)]
    dependency_payload = [finding.model_dump() for finding in dependency_findings]
    code_payload = [finding.model_dump() for finding in code_findings]
    pr_payload = [finding.model_dump() for finding in pr_findings]

    write_state_section("security_issues", security_issues)
    write_state_section("dependency_findings", dependency_payload)
    write_state_section("code_scanning_findings", code_payload)
    write_state_section("dependabot_prs", pr_payload)

    return ToolResult(
        ok=True,
        fatal=False,
        message="audit fan-out completed",
        data={
            "security_issues": security_issues,
            "dependency_findings": dependency_payload,
            "code_scanning_findings": code_payload,
        },
        reasoning_summary="Collected compact GitHub security inputs concurrently.",
    )
