import json
import re
import subprocess
import sys

from google.antigravity import ToolContext

from src.config.config import SeccureState
from src.utils.git_tools import get_commit_messages
from src.utils.mcp_client import get_mcp_manager


async def list_dependabot_prs(ctx: ToolContext) -> str:
    """Fetch all open pull requests authored by dependabot[bot]."""
    cached = ctx.get_state("raw_dependabot_prs")
    if cached:
        return cached

    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    query = f"repo:{owner}/{repo} is:pr state:open author:app/dependabot"
    try:
        data = await manager.call_tool_with_retry(
            "search_pull_requests", {"query": query, "perPage": 30}
        )
    except Exception as e:
        print(f"[Seccure] Warning: search_pull_requests failed: {e}", file=sys.stderr)
        return "[]"

    if not data or not isinstance(data, list) or "text" not in data[0]:
        return "[]"

    items_text = data[0]["text"]
    if items_text.startswith("failed to "):
        print(f"[Seccure] search_pull_requests error: {items_text}", file=sys.stderr)
        return "[]"

    try:
        items = json.loads(items_text)
    except json.JSONDecodeError:
        return "[]"

    results = []
    if items:
        if len(items) == 30:
            msg = "[Seccure] Warning: Dependabot PRs truncated to 30 items."
            print(msg, file=sys.stderr)
            ctx.set_state("dependabot_prs_warning", msg)

        for pr in items:
            title = pr.get("title", "")
            pkg, from_v, to_v = _parse_dependabot_title(title)
            results.append(
                {
                    "number": pr.get("number"),
                    "title": title,
                    "package": pkg,
                    "from_version": from_v,
                    "to_version": to_v,
                    "html_url": pr.get("url", "") or pr.get("html_url", ""),
                }
            )

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
# PR Write tools
# ---------------------------------------------------------------------------

ATTEMPT_MARKER = "<!-- seccure-attempt-count:"
_ATTEMPT_RE = re.compile(r"<!--\s*seccure-attempt-count:(\d+)\s*-->")


def _get_owner_repo() -> tuple[str, str]:
    import os

    repo_env = os.environ.get("TARGET_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if repo_env:
        parts = repo_env.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]

    try:
        res = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = res.stdout.strip()
        if url.startswith("https://github.com/") or url.startswith("git@github.com:"):
            path = url.split("github.com")[-1].lstrip(":/")
            path = path.removesuffix(".git")
            parts = path.split("/")
            if len(parts) == 2:
                return parts[0], parts[1]
    except Exception:
        pass

    raise ValueError("Could not determine repository owner and name.")


async def check_existing_seccure_pr() -> str:
    """Check whether an open PR with the 'seccure' label already exists."""
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    query = f"repo:{owner}/{repo} is:pr state:open label:seccure"
    try:
        data = await manager.call_tool_with_retry(
            "search_pull_requests", {"query": query, "perPage": 1}
        )
        items_text = data[0]["text"]
        items = json.loads(items_text)
    except Exception:
        items = []

    if items and isinstance(items, list) and len(items) > 0:
        pr = items[0]
        return json.dumps(
            {
                "found": True,
                "pr_number": pr.get("number"),
                "url": pr.get("html_url", pr.get("url", "")),
                "body": pr.get("body", ""),
                "attempt_count": extract_attempt_count(pr.get("body", "")),
            }
        )

    return json.dumps(
        {"found": False, "pr_number": None, "url": None, "body": "", "attempt_count": 0}
    )


def extract_attempt_count(body: str) -> int:
    match = _ATTEMPT_RE.search(body or "")
    return int(match.group(1)) if match else 0


def with_attempt_marker(body: str, attempt_count: int) -> str:
    marker = f"<!-- seccure-attempt-count:{attempt_count} -->"
    if _ATTEMPT_RE.search(body):
        return _ATTEMPT_RE.sub(marker, body)
    return f"{body.rstrip()}\n\n{marker}\n"


def render_pr_title_body(
    state: SeccureState, commit_references: list[str] | None = None
) -> tuple[str, str]:
    fixed_rows = []
    for result in state.fix_results:
        if not result.fixed:
            continue
        row_template = "| {package} | {from_version} | {to_version} | {strategy} | {cve} | {severity} |"
        fixed_rows.append(
            row_template.format(
                package=result.package,
                from_version=result.from_version,
                to_version=result.to_version or "",
                strategy=result.strategy,
                cve=result.cve_id or "",
                severity=result.severity or "",
            )
        )
    if not fixed_rows:
        fixed_rows.append("| _No package changes_ |  |  |  |  |  |")

    conflict_lines = []
    for issue_number in state.conflict_issue_numbers:
        conflict_lines.append(f"- #{issue_number}")

    pr_closes = []
    for pr in state.dependabot_prs:
        pr_number = getattr(pr, "pr_number", None)
        if pr_number:
            pr_closes.append(f"- Closes #{pr_number}")
    if not pr_closes:
        pr_closes.append("- None")

    issue_closes = [
        f"- Closes #{issue.issue_number}" for issue in state.security_issues
    ]
    if not issue_closes:
        issue_closes.append("- None")

    title = "fix(deps): automated Seccure security updates"
    body = f"""## Seccure Automated Security Patch

Auto-generated by the Seccure Agent.

### Packages Fixed
| Package | From | To | Strategy | CVE | Severity |
|---------|------|----|----------|-----|----------|
{chr(10).join(fixed_rows)}
"""

    if conflict_lines:
        body += "\n### Could Not Auto-Fix\n" + "\n".join(conflict_lines) + "\n"

    body += f"""
### Closes Dependabot PRs
{chr(10).join(pr_closes)}

### Closes Issues
{chr(10).join(issue_closes)}
"""

    if commit_references:
        commit_lines = [f"- #{ref}" for ref in commit_references]
        body += f"\n### Mentions from Commits\n{chr(10).join(commit_lines)}\n"

    body += """
---
PRs created by GITHUB_TOKEN may not trigger CI workflows automatically.
"""
    return title, with_attempt_marker(body, state.attempt_count)


async def close_seccure_pr(pr_number: int) -> str:
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    try:
        await manager.call_tool_with_retry(
            "add_issue_comment",
            {
                "owner": owner,
                "repo": repo,
                "issue_number": pr_number,
                "body": "🔄 **Seccure Agent** is re-running and has superseded this PR.\n\nA fresh, up-to-date fix PR will be opened shortly.",
            },
        )

        await manager.call_tool_with_retry(
            "update_pull_request",
            {"owner": owner, "repo": repo, "pullNumber": pr_number, "state": "closed"},
        )
    except Exception as e:
        print(f"[Seccure] Warning: close_seccure_pr failed: {e}", file=sys.stderr)
        return f"Failed to close PR #{pr_number}: {e}"

    return f"Closed existing Seccure PR #{pr_number}."


def get_default_branch() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = res.stdout.strip().replace("origin/", "")
        if branch:
            return branch
    except Exception:
        pass
    return "main"


async def create_pull_request(
    title: str, body: str, head_branch: str, base_branch: str
) -> str:
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    res = await manager.call_tool_with_retry(
        "create_pull_request",
        {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        },
    )

    output_text = res[0]["text"]
    try:
        pr_data = json.loads(output_text)
        return json.dumps(
            {
                "pr_number": pr_data.get("number"),
                "url": pr_data.get("html_url", pr_data.get("url")),
            }
        )
    except json.JSONDecodeError:
        return json.dumps({"pr_number": 0, "url": output_text})


async def update_pull_request(pr_number: int, title: str, body: str) -> str:
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    res = await manager.call_tool_with_retry(
        "update_pull_request",
        {
            "owner": owner,
            "repo": repo,
            "pullNumber": pr_number,
            "title": title,
            "body": body,
        },
    )

    output_text = res[0]["text"]
    try:
        pr_data = json.loads(output_text)
        return json.dumps(
            {
                "pr_number": pr_data.get("number"),
                "url": pr_data.get("html_url", pr_data.get("url")),
            }
        )
    except json.JSONDecodeError:
        return json.dumps({"pr_number": pr_number, "url": output_text})


async def _add_labels(pr_number: int, labels: list[str]) -> str:
    """Since MCP doesn't have an 'add_label' tool directly, we might need issue_write"""
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()
    try:
        # issue_write update can add labels
        await manager.call_tool_with_retry(
            "issue_write",
            {
                "method": "update",
                "owner": owner,
                "repo": repo,
                "issue_number": pr_number,
                "labels": labels,
            },
        )
        return f"Labels {labels} added to #{pr_number}."
    except Exception as e:
        print(f"Warning: Failed to add labels to PR: {e}", file=sys.stderr)
        return str(e)


async def upsert_seccure_pr(
    state_json: str,
    head_branch: str,
    base_branch: str,
    existing_pr_number: int | None = None,
) -> str:
    state = SeccureState.model_validate_json(state_json)

    messages = get_commit_messages(base_branch, head_branch)
    refs = extract_references_from_commits(messages)

    # Skip bulk validation for now, or just return them
    valid_refs = refs

    title, new_automated_body = render_pr_title_body(
        state, commit_references=valid_refs
    )

    final_body = new_automated_body
    if existing_pr_number:
        owner, repo = _get_owner_repo()
        manager = get_mcp_manager()
        try:
            view_data_res = await manager.call_tool_with_retry(
                "issue_read",
                {
                    "method": "get",
                    "owner": owner,
                    "repo": repo,
                    "issue_number": existing_pr_number,
                },
            )
            existing_body = json.loads(view_data_res[0]["text"]).get("body", "")

            marker_match = _ATTEMPT_RE.search(existing_body)
            if marker_match:
                manual_text = existing_body[: marker_match.start()].strip()
                if manual_text:
                    auto_start = manual_text.find("## Seccure Automated Security Patch")
                    if auto_start != -1:
                        manual_text = manual_text[:auto_start].strip()
                    if manual_text:
                        final_body = f"{manual_text}\\n\\n{new_automated_body}"
        except Exception as e:
            print(
                f"[Seccure] Warning: Could not fetch existing PR body: {e}",
                file=sys.stderr,
            )

        result = await update_pull_request(existing_pr_number, title, final_body)
    else:
        result = await create_pull_request(title, final_body, head_branch, base_branch)

    data = json.loads(result)
    pr_num = data.get("pr_number")
    if pr_num:
        await _add_labels(pr_num, ["seccure", "auto-fix", "dependabot"])
    return result


def extract_references_from_commits(messages: list[str]) -> list[str]:
    """
    Parses commit messages to find issue and PR references like #123 or GH-123.
    """
    refs = set()
    pattern = re.compile(r"(?:#|GH-|PR-)(\d+)", re.IGNORECASE)
    for msg in messages:
        for match in pattern.finditer(msg):
            refs.add(match.group(1))
    return sorted(refs, key=int)


def fetch_ci_logs_for_pr(pr_number: int) -> str:
    # Cannot easily fetch CI logs via standard MCP tools.
    # Return placeholder.
    return "CI log fetching is not supported natively via MCP yet."
