import json
import os
import subprocess
from datetime import date

from src.utils.mcp_client import get_mcp_manager


def _get_owner_repo() -> tuple[str, str]:
    repo_env = os.environ.get("TARGET_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if repo_env:
        parts = repo_env.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]

    # Fallback
    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = res.stdout.strip()
        # e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git
        if url.startswith("https://github.com/") or url.startswith("git@github.com:"):
            path = url.split("github.com")[-1].lstrip(":/")
            path = path.removesuffix(".git")
            parts = path.split("/")
            if len(parts) == 2:
                return parts[0], parts[1]
    except Exception:
        pass

    raise ValueError(
        "Could not determine repository owner and name from environment or git remote."
    )


_security_issues_cache = None


async def list_security_issues() -> str:
    """Fetch all open GitHub issues labelled 'security' or 'dependabot'.
    Excludes pull requests. Deduplicates by issue number.
    Uses ToolContext caching to avoid duplicate API calls within one turn.
    """
    global _security_issues_cache
    if _security_issues_cache is not None:
        return _security_issues_cache

    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()
    results = []
    seen = set()

    for label in ("security", "dependabot"):
        query = f"repo:{owner}/{repo} is:issue state:open label:{label}"
        try:
            data = await manager.call_tool_with_retry(
                "search_issues", {"query": query, "perPage": 30}
            )
        except Exception as e:
            # If tool fails, just continue
            import sys

            print(f"[Seccure] Warning: search_issues tool failed: {e}", file=sys.stderr)
            continue

        if not data or not isinstance(data, list) or "text" not in data[0]:
            continue

        items_text = data[0]["text"]

        # If it returned an error string instead of JSON
        if items_text.startswith("failed to "):
            import sys

            print(f"[Seccure] search_issues error: {items_text}", file=sys.stderr)
            continue

        try:
            items = json.loads(items_text)
        except json.JSONDecodeError:
            continue

        if len(items) == 30:
            import sys

            msg = f"[Seccure] Warning: Security issues for label '{label}' truncated to 30 items."
            print(msg, file=sys.stderr)

        for issue in items:
            num = issue.get("number")
            if not num or num in seen:
                continue
            seen.add(num)

            # search_issues might return limited fields, ensure we get title/labels/url
            # Sometimes labels might not be included in search results, so we do our best.
            labels = issue.get("labels", [])
            if (
                isinstance(labels, list)
                and len(labels) > 0
                and isinstance(labels[0], dict)
            ):
                labels = [lb.get("name") for lb in labels]

            results.append(
                {
                    "number": num,
                    "title": issue.get("title", ""),
                    "labels": labels,
                    "html_url": issue.get("url") or issue.get("html_url", ""),
                }
            )

    payload = json.dumps(results)
    _security_issues_cache = payload
    return payload


async def create_conflict_issue(
    package: str,
    cve_id: str,
    severity: str,
    advisory_url: str,
    reason: str,
) -> str:
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
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    title = f"🚨 Unresolved vulnerability: {package} ({cve_id})"

    res = await manager.call_tool_with_retry(
        "issue_write",
        {
            "method": "create",
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
            "labels": ["security", "conflict", "seccure"],
        },
    )

    # Extract output URL and issue number
    if res and isinstance(res, list) and "text" in res[0]:
        output_text = res[0]["text"]
        try:
            issue_data = json.loads(output_text)
            return json.dumps(
                {
                    "issue_number": issue_data.get("number"),
                    "url": issue_data.get("html_url") or issue_data.get("url"),
                }
            )
        except json.JSONDecodeError:
            return json.dumps({"issue_number": 0, "url": output_text})
    return json.dumps({"issue_number": 0, "url": str(res)})
