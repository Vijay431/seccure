import json
import sys

from src.utils.github_issues import _get_owner_repo
from src.utils.mcp_client import get_mcp_manager


async def list_dependabot_alerts() -> str:
    """Fetch all open Dependabot vulnerability alerts."""
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    try:
        data = await manager.call_tool_with_retry(
            "list_dependabot_alerts", {"owner": owner, "repo": repo, "state": "open", "perPage": 100}
        )
    except Exception as e:
        print(f"[Seccure] Warning: list_dependabot_alerts failed: {e}", file=sys.stderr)
        return "[]"

    if not data or not isinstance(data, list) or "text" not in data[0]:
        return "[]"

    items_text = data[0]["text"]
    if items_text.startswith("failed to "):
        print(f"[Seccure] list_dependabot_alerts error: {items_text}", file=sys.stderr)
        return "[]"

    try:
        json.loads(items_text)
        return items_text
    except json.JSONDecodeError:
        return "[]"


async def list_code_scanning_alerts() -> str:
    """Fetch all open code-scanning alerts."""
    owner, repo = _get_owner_repo()
    manager = get_mcp_manager()

    try:
        data = await manager.call_tool_with_retry(
            "list_code_scanning_alerts", {"owner": owner, "repo": repo, "state": "open", "perPage": 100}
        )
    except Exception as e:
        print(f"[Seccure] Warning: list_code_scanning_alerts failed: {e}", file=sys.stderr)
        return "[]"

    if not data or not isinstance(data, list) or "text" not in data[0]:
        return "[]"

    items_text = data[0]["text"]
    if items_text.startswith("failed to ") or "not enabled" in items_text.lower() or "no analysis" in items_text.lower():
        print(f"[Seccure] list_code_scanning_alerts error/not-enabled: {items_text}", file=sys.stderr)
        return "[]"

    try:
        json.loads(items_text)
        return items_text
    except json.JSONDecodeError:
        return "[]"
