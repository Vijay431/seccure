"""GitHub API write tools used exclusively by the Coordinator agent."""

from __future__ import annotations

import json
import os
from datetime import date

from agent.tools.github_client import get, patch, post


def _repo() -> str:
    return os.environ["TARGET_REPO"]


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------


def check_existing_seccure_pr() -> str:
    """Check whether an open PR with the 'seccure' label already exists.

    Returns:
        JSON string with: found (bool), pr_number (int or null), url (str or null).
    """
    repo = _repo()
    prs = get(f"/repos/{repo}/pulls", state="open", per_page=100)
    if not isinstance(prs, list):
        return json.dumps({"found": False, "pr_number": None, "url": None})

    for pr in prs:
        labels = [lb["name"] for lb in pr.get("labels", [])]
        if "seccure" in labels:
            return json.dumps(
                {"found": True, "pr_number": pr["number"], "url": pr["html_url"]}
            )

    return json.dumps({"found": False, "pr_number": None, "url": None})


def close_seccure_pr(pr_number: int) -> str:
    """Close an existing Seccure PR with an explanatory comment.

    Args:
        pr_number: The pull request number to close.

    Returns:
        Confirmation message.
    """
    repo = _repo()
    post(
        f"/repos/{repo}/issues/{pr_number}/comments",
        {
            "body": (
                "🔄 **Seccure Agent** is re-running and has superseded this PR.\n\n"
                "A fresh, up-to-date fix PR will be opened shortly."
            )
        },
    )
    patch(f"/repos/{repo}/pulls/{pr_number}", {"state": "closed"})
    return f"Closed existing Seccure PR #{pr_number}."


# ---------------------------------------------------------------------------
# Repository metadata
# ---------------------------------------------------------------------------


def get_default_branch() -> str:
    """Get the default branch name of the target repository.

    Returns:
        The default branch name (e.g. 'main' or 'master').
    """
    data = get(f"/repos/{_repo()}")
    return str(data.get("default_branch", "main"))


# ---------------------------------------------------------------------------
# PR creation
# ---------------------------------------------------------------------------


def create_pull_request(title: str, body: str, head_branch: str, base_branch: str) -> str:
    """Create the consolidated security fix pull request.

    Args:
        title: The PR title.
        body: Full markdown PR body. Must contain Closes #N references.
        head_branch: The fix branch to merge from.
        base_branch: The target base branch (default branch).

    Returns:
        JSON string with: pr_number, url.
    """
    data = post(
        f"/repos/{_repo()}/pulls",
        {"title": title, "body": body, "head": head_branch, "base": base_branch},
    )
    return json.dumps({"pr_number": data["number"], "url": data["html_url"]})


def add_labels(pr_number: int, labels: list[str]) -> str:
    """Add labels to a pull request or issue.

    Args:
        pr_number: The PR or issue number.
        labels: List of label name strings to add.

    Returns:
        Confirmation message.
    """
    post(f"/repos/{_repo()}/issues/{pr_number}/labels", {"labels": labels})
    return f"Labels {labels} added to #{pr_number}."


# ---------------------------------------------------------------------------
# Conflict issue creation
# ---------------------------------------------------------------------------


def create_conflict_issue(
    package: str,
    cve_id: str,
    severity: str,
    advisory_url: str,
    reason: str,
) -> str:
    """Create a GitHub issue for a vulnerability that could not be auto-fixed.

    Args:
        package: The npm package name.
        cve_id: The CVE or GHSA identifier.
        severity: Severity level (low/medium/high/critical).
        advisory_url: URL to the security advisory.
        reason: Human-readable explanation of why the fix failed.

    Returns:
        JSON string with: issue_number, url.
    """
    today = date.today().isoformat()
    body = f"""## 🚨 Unresolved Vulnerability: `{package}`

Seccure Agent attempted all fix strategies and failed.

| Field | Value |
|-------|-------|
| Package | `{package}` |
| CVE | [{cve_id}]({advisory_url}) |
| Severity | `{severity}` |
| Strategies tried | npm audit fix, npm overrides, manual bump |
| Reason | {reason} |

### Recommended Manual Action
1. Run `npm ls {package}` to trace the dependency chain
2. Check if a major version upgrade of the parent dependency resolves this
3. Consider replacing the dependency if no fix is available

---
> Created by Seccure Agent on {today}.
"""
    data = post(
        f"/repos/{_repo()}/issues",
        {
            "title": f"🚨 Unresolved vulnerability: {package} ({cve_id})",
            "body": body,
            "labels": ["security", "conflict", "seccure"],
        },
    )
    return json.dumps({"issue_number": data["number"], "url": data["html_url"]})
