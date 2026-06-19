import json
from datetime import date

from google.antigravity import ToolContext

from src.utils.gh_wrapper_v2 import run_gh_command


def list_security_issues(ctx: ToolContext) -> str:
    """Fetch all open GitHub issues labelled 'security' or 'dependabot'.
    Excludes pull requests. Deduplicates by issue number.
    Uses ToolContext caching to avoid duplicate API calls within one turn.
    """
    cached = ctx.get_state("raw_security_issues")
    if cached:
        return cached

    results = []
    seen = set()

    for label in ("security", "dependabot"):
        data = run_gh_command([
            "issue", "list",
            "--label", label,
            "--state", "open",
            "--limit", "30",
            "--json", "number,title,labels,url"
        ])
        if not data:
            continue

        if len(data) == 30:
            import sys
            msg = f"[Seccure] Warning: Security issues for label '{label}' truncated to 30 items."
            print(msg, file=sys.stderr)
            ctx.set_state(f"issues_warning_{label}", msg)

        for issue in data:
            num = issue["number"]
            if num in seen:
                continue
            seen.add(num)
            results.append({
                "number": num,
                "title": issue["title"],
                "labels": [lb["name"] for lb in issue.get("labels", [])],
                "html_url": issue.get("url") or issue.get("html_url", "")
            })

    payload = json.dumps(results)
    ctx.set_state("raw_security_issues", payload)
    return payload

def create_conflict_issue(
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
    # Create issue with gh
    data = run_gh_command([
        "issue", "create",
        "--title", f"🚨 Unresolved vulnerability: {package} ({cve_id})",
        "--body", body,
        "--label", "security,conflict,seccure"
    ])
    # gh issue create doesn't support --json. It outputs the URL.
    # We can fetch the issue number from the URL or just fetch the latest issue.
    # It outputs just the URL to stdout if not tty, let's extract the number.

    # Actually we can do gh issue view <url> --json number,url
    url = data.strip()
    issue_data = run_gh_command(["issue", "view", url, "--json", "number,url"])
    return json.dumps({"issue_number": issue_data["number"], "url": issue_data["url"]})
