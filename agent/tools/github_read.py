"""GitHub API read tools for the three subagents.

Each function uses ToolContext caching to avoid duplicate API calls within
the same agent turn.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from google.antigravity import ToolContext

from agent.tools.github_client import get, get_text


def _repo() -> str:
    return os.environ["TARGET_REPO"]


# ---------------------------------------------------------------------------
# IssueAgent tool
# ---------------------------------------------------------------------------


def list_security_issues(ctx: ToolContext) -> str:
    """Fetch all open GitHub issues labelled 'security' or 'dependabot'.

    Excludes pull requests. Deduplicates by issue number.
    Uses ToolContext caching to avoid duplicate API calls within one turn.

    Returns:
        JSON array of objects with fields: number, title, labels, html_url.
    """
    cached = ctx.get_state("raw_security_issues")
    if cached:
        return cached

    repo = _repo()
    seen: set[int] = set()
    results: list[dict[str, Any]] = []

    for label in ("security", "dependabot"):
        page = 1
        while True:
            batch = get(
                f"/repos/{repo}/issues",
                state="open",
                labels=label,
                per_page=100,
                page=page,
            )
            if not isinstance(batch, list) or not batch:
                break
            for issue in batch:
                if "pull_request" in issue:
                    continue
                num = issue["number"]
                if num in seen:
                    continue
                seen.add(num)
                results.append(
                    {
                        "number": num,
                        "title": issue["title"],
                        "labels": [lb["name"] for lb in issue.get("labels", [])],
                        "html_url": issue["html_url"],
                    }
                )
            if len(batch) < 100:
                break
            page += 1

    payload = json.dumps(results)
    ctx.set_state("raw_security_issues", payload)
    return payload


# ---------------------------------------------------------------------------
# PRAgent tool
# ---------------------------------------------------------------------------


def list_dependabot_prs(ctx: ToolContext) -> str:
    """Fetch all open pull requests authored by dependabot[bot].

    Parses the PR title to extract package name and version bump.

    Returns:
        JSON array with fields: number, title, package, from_version,
        to_version, html_url.
    """
    cached = ctx.get_state("raw_dependabot_prs")
    if cached:
        return cached

    repo = _repo()
    results = []
    page = 1

    while True:
        batch = get(f"/repos/{repo}/pulls", state="open", per_page=100, page=page)
        if not isinstance(batch, list) or not batch:
            break
        for pr in batch:
            login = pr.get("user", {}).get("login", "")
            if "dependabot" in login.lower():
                title: str = pr.get("title", "")
                pkg, from_v, to_v = _parse_dependabot_title(title)
                results.append(
                    {
                        "number": pr["number"],
                        "title": title,
                        "package": pkg,
                        "from_version": from_v,
                        "to_version": to_v,
                        "html_url": pr["html_url"],
                    }
                )
        if len(batch) < 100:
            break
        page += 1

    payload = json.dumps(results)
    ctx.set_state("raw_dependabot_prs", payload)
    return payload


def _parse_dependabot_title(title: str) -> tuple[str, str, str]:
    """Extract package, from_version, to_version from a Dependabot PR title."""
    match = re.search(
        r"(?:bump|update)\s+(?P<pkg>[\w@/.-]+)(?:\s+requirement)?\s+from\s+(?P<from>[<>=^\~]*[\d.\w-]+)\s+to\s+(?P<to>[<>=^\~]*[\d.\w-]+)",
        title,
        re.IGNORECASE,
    )
    if match:
        return match.group("pkg"), match.group("from"), match.group("to")
    return title, "unknown", "unknown"


# ---------------------------------------------------------------------------
# SecurityAgent tools
# ---------------------------------------------------------------------------


def list_dependabot_alerts(ctx: ToolContext) -> str:
    """Fetch all open Dependabot vulnerability alerts for the npm ecosystem.

    Deduplicates by CVE ID.

    Returns:
        JSON array with fields: alert_number, cve_id, package, severity,
        patched_version, advisory_url.
    """
    cached = ctx.get_state("raw_dependabot_alerts")
    if cached:
        return cached

    repo = _repo()
    results = []
    page = 1

    while True:
        try:
            batch = get(
                f"/repos/{repo}/dependabot/alerts",
                state="open",
                per_page=100,
                page=page,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                raise PermissionError(
                    "GitHub Dependabot alerts API returned 403; "
                    "security_events permission is required."
                ) from exc
            if exc.response.status_code == 404:
                batch = []
            else:
                raise

        if not isinstance(batch, list) or not batch:
            break
        for alert in batch:
            sa = alert.get("security_advisory", {})
            sv = alert.get("security_vulnerability", {})
            identifiers = sa.get("identifiers", [])
            cve_id = next(
                (i["value"] for i in identifiers if i["type"] == "CVE"),
                sa.get("ghsa_id", "UNKNOWN"),
            )
            first_patched = sv.get("first_patched_version")
            results.append(
                {
                    "alert_number": alert["number"],
                    "cve_id": cve_id,
                    "package": sv.get("package", {}).get("name", "unknown"),
                    "ecosystem": sv.get("package", {}).get("ecosystem", "unknown"),
                    "severity": sa.get("severity", "unknown"),
                    "patched_version": (
                        first_patched.get("identifier") if first_patched else None
                    ),
                    "advisory_url": sa.get("html_url", ""),
                }
            )
        if len(batch) < 100:
            break
        page += 1

    payload = json.dumps(results)
    ctx.set_state("raw_dependabot_alerts", payload)
    return payload


def list_code_scanning_alerts(ctx: ToolContext) -> str:
    """Fetch all open code-scanning alerts. Returns empty array if not enabled.

    Returns:
        JSON array with fields: number, rule_id, severity, description, url.
    """
    cached = ctx.get_state("raw_code_scanning_alerts")
    if cached:
        return cached

    repo = _repo()
    try:
        batch = get(f"/repos/{repo}/code-scanning/alerts", state="open", per_page=100)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            raise PermissionError(
                "GitHub code scanning API returned 403; "
                "security_events permission is required."
            ) from exc
        if exc.response.status_code != 404:
            raise
        print("[Seccure] Warning: code scanning alerts unavailable; treating as empty.")
        payload = json.dumps([])
        ctx.set_state("raw_code_scanning_alerts", payload)
        return payload

    if not isinstance(batch, list):
        payload = json.dumps([])
        ctx.set_state("raw_code_scanning_alerts", payload)
        return payload

    results = [
        {
            "number": a["number"],
            "rule_id": a.get("rule", {}).get("id", "unknown"),
            "severity": a.get("rule", {}).get("severity", "unknown"),
            "description": a.get("rule", {}).get("description", ""),
            "url": a.get("html_url", ""),
        }
        for a in batch
    ]

    payload = json.dumps(results)
    ctx.set_state("raw_code_scanning_alerts", payload)
    return payload


def fetch_ci_logs_for_pr(pr_number: int) -> str:
    """Fetch GitHub Action CI logs for the failed checks on a PR.

    Args:
        pr_number: The pull request number.

    Returns:
        A concatenated string of the tail of the logs from all failed jobs.
    """
    repo = _repo()
    try:
        pr = get(f"/repos/{repo}/pulls/{pr_number}")
    except Exception as e:
        return f"Error fetching PR: {e}"

    head_sha = pr.get("head", {}).get("sha")
    if not head_sha:
        return "PR head sha not found."

    try:
        checks = get(f"/repos/{repo}/commits/{head_sha}/check-runs")
    except Exception as e:
        return f"Error fetching check runs: {e}"

    if not isinstance(checks, dict):
        return "Invalid check runs response."

    runs = checks.get("check_runs", [])
    failed_runs = [r for r in runs if r.get("conclusion") in ("failure", "timed_out")]

    if not failed_runs:
        return "No failed check runs found. Pipeline might be green or still running."

    logs_summary = []
    for run in failed_runs:
        job_id = run.get("id")
        name = run.get("name", "Unknown Job")
        logs_summary.append(f"--- Logs for failed job: {name} (ID: {job_id}) ---")
        try:
            log_text = get_text(f"/repos/{repo}/actions/jobs/{job_id}/logs")
            # The log might be huge. Grab the last 5000 characters
            logs_summary.append(log_text[-5000:])
        except Exception as e:
            logs_summary.append(f"Could not fetch logs: {e}")

    return "\n\n".join(logs_summary)
