import os
from pathlib import Path

from src.utils.mcp_client import get_mcp_manager


async def read_repo_constraints() -> str:
    """Read the repo-specific constraints file and the ADDITIONAL_CONSTRAINTS env var."""
    parts: list[str] = []

    constraints_dir = os.environ.get("SECCURE_CONSTRAINTS_DIR", "")
    content = ""
    if constraints_dir:
        constraints_file = Path(constraints_dir) / "constraints.md"
        if constraints_file.exists():
            content = constraints_file.read_text().strip()
    else:
        repo_env = os.environ.get("TARGET_REPO") or os.environ.get(
            "GITHUB_REPOSITORY", ""
        )
        if repo_env and "/" in repo_env:
            owner, repo = repo_env.split("/", 1)
            manager = get_mcp_manager()
            try:
                res = await manager.call_tool_with_retry(
                    "get_file_contents",
                    {"owner": owner, "repo": repo, "path": ".seccure/constraints.md"},
                )
                # get_file_contents returns decoded content in the text field or we might need to parse json
                # The MCP server usually returns file content directly in text.
                if res and isinstance(res, list) and "text" in res[0]:
                    text_out = res[0]["text"]
                    if not text_out.startswith("failed to "):
                        content = text_out.strip()
            except Exception as e:
                import sys

                print(
                    f"[Seccure] Warning: failed to fetch constraints.md from API: {e}",
                    file=sys.stderr,
                )

    if content:
        parts.append(f"## From .seccure/constraints.md\n\n{content}")

    extra = os.environ.get("ADDITIONAL_CONSTRAINTS", "").strip()
    if extra:
        parts.append(f"## Additional constraints (this run only)\n\n{extra}")

    return "\n\n".join(parts)


async def load_constraints_text() -> str:
    """Non-tool version of read_repo_constraints() for use in main.py."""
    return await read_repo_constraints()
