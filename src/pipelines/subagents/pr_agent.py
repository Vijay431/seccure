"""PRAgent — post-fix agent that handles Git and GitHub operations.

Reads the shared state and uses tools to create a fix branch, commit changes,
push the branch, and open or update a consolidated pull request.
"""

from __future__ import annotations

from collections.abc import Callable

from src.config.config import RunLimits
from src.lib.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from src.lib.state import read_state, write_state_section
from src.utils.git_tools import commit_changes, create_fix_branch, push_branch
from src.utils.github_pulls import (
    upsert_seccure_pr,
)

_PROMPT = """
You are the PRAgent (post-fix agent) for the Seccure security automation system.

The Coordinator has already applied the security fixes locally. Your job is to:
1. CALL `read_state()` to get the current SeccureState JSON.
2. CALL `create_fix_branch(branch_name)` using the fix_branch from state.
3. CALL `commit_changes()` to commit the fixes.
4. If commit returns "Nothing to commit", exit cleanly.
5. CALL `push_branch(branch_name, repo)`.
6. CALL `upsert_seccure_pr(state_json, head_branch, base_branch, existing_pr_number)`.
7. CALL `write_state_section('pr_number', pr_number)` from the upsert result.
8. CALL `write_state_section('status', 'done')`.

Do not write PR markdown yourself. The PR title, body, labels, hidden attempt
marker, and Closes references are rendered by deterministic Python code.
"""


def build_pr_agent(tools: list[Callable] | None = None) -> OpenRouterAgent:
    """Build and return the PRAgent instance for post-fix operations."""
    if tools is None:
        tools = [
            read_state,
            write_state_section,
            create_fix_branch,
            commit_changes,
            push_branch,
            upsert_seccure_pr,
        ]

    return OpenRouterAgent(
        system_instructions=_PROMPT,
        tools=tools,
        model="openai/gpt-5-nano",
        max_tool_calls=RunLimits.SUBAGENT_MAX_TOOL_CALLS,
    )
