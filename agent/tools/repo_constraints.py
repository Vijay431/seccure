"""Tool to read repo-specific constraints from .seccure/constraints.md.

Constraints are optional free-text rules that repo maintainers write to
control how Seccure fixes vulnerabilities (e.g. 'do not upgrade TypeScript
to a major version').
"""

from __future__ import annotations

import os
from pathlib import Path


def read_repo_constraints() -> str:
    """Read the repo-specific constraints file and the ADDITIONAL_CONSTRAINTS env var.

    Fetches .seccure/constraints.md from the target repository via the GitHub API,
    or reads it locally if SECCURE_CONSTRAINTS_DIR is set.

    Merges file-based constraints with any one-off constraints passed via
    the ADDITIONAL_CONSTRAINTS env var (workflow_dispatch input).

    Returns:
        Combined constraints text, or empty string if no constraints found.
    """
    import base64
    from httpx import HTTPStatusError
    from agent.tools.github_client import get

    parts: list[str] = []

    # 1. File-based constraints (.seccure/constraints.md)
    constraints_dir = os.environ.get("SECCURE_CONSTRAINTS_DIR", "")
    content = ""
    if constraints_dir:
        constraints_file = Path(constraints_dir) / "constraints.md"
        if constraints_file.exists():
            content = constraints_file.read_text().strip()
    else:
        # Fetch from GitHub API
        repo = os.environ.get("TARGET_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
        if repo:
            try:
                resp = get(f"/repos/{repo}/contents/.seccure/constraints.md")
                if isinstance(resp, dict) and resp.get("type") == "file" and "content" in resp:
                    content = base64.b64decode(resp["content"]).decode("utf-8").strip()
            except HTTPStatusError as e:
                if e.response.status_code != 404:
                    print(f"[Seccure] Warning: failed to fetch constraints.md from API: {e}")

    if content:
        parts.append(f"## From .seccure/constraints.md\n\n{content}")

    # 2. One-off constraints from workflow_dispatch input
    extra = os.environ.get("ADDITIONAL_CONSTRAINTS", "").strip()
    if extra:
        parts.append(f"## Additional constraints (this run only)\n\n{extra}")

    return "\n\n".join(parts)


def load_constraints_text() -> str:
    """Non-tool version of read_repo_constraints() for use in main.py."""
    return read_repo_constraints()
