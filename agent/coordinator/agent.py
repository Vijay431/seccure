"""Coordinator agent builder.

Assembles the Coordinator with all tools, policies, and hooks.
The system prompt is passed in dynamically from main.py so that
repo-specific constraints can be injected at runtime.
"""

from __future__ import annotations

from agent.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from agent.state import read_state, write_state_section
from agent.subagents.audit_fanout import run_audit_fanout
from agent.tools.git_tools import (
    apply_package_override,
    bump_package_version,
    check_remaining_vulnerabilities,
    clone_repo,
    ensure_lockfile,
    run_auto_fix,
)
from agent.tools.github_pulls import fetch_ci_logs_for_pr
from agent.tools.github_pulls import (
    check_existing_seccure_pr,
    close_seccure_pr,
    get_default_branch,
)
from agent.tools.github_issues import create_conflict_issue
from agent.tools.observability import log_token_usage
from agent.tools.repo_constraints import read_repo_constraints


def build_coordinator(system_prompt: str) -> OpenRouterAgent:
    """Build and return the Coordinator agent instance.

    Args:
        system_prompt: Dynamically assembled system prompt
                       (base prompt + optional repo constraints).

    Returns:
        Configured OpenRouter agent ready to be used as an async context manager.
    """
    tools_list = [
        # Shared state
        read_state,
        write_state_section,
        run_audit_fanout,
        # Constraints (can be re-read mid-run if needed)
        read_repo_constraints,
        # Idempotency guard
        check_existing_seccure_pr,
        close_seccure_pr,
        # Repo metadata
        get_default_branch,
        # Git / npm operations
        clone_repo,
        ensure_lockfile,
        run_auto_fix,
        apply_package_override,
        bump_package_version,
        check_remaining_vulnerabilities,
        # GitHub write operations
        create_conflict_issue,
        fetch_ci_logs_for_pr,
        # Observability
        log_token_usage,
    ]

    import os

    # Add LangSmith tracing to tools if enabled
    if os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        try:
            from langsmith import traceable
            tools_list = [traceable(t) if callable(t) else t for t in tools_list]
        except ImportError:
            print("[Seccure] Warning: langsmith not installed. Skipping tracing.")

    async def invoke_subagent(TypeName: str, Role: str, Prompt: str) -> str:
        if TypeName == "PRAgent":
            from agent.subagents.pr_agent import build_pr_agent
            agent = build_pr_agent()
        else:
            return (
                "Error: audit subagents are now invoked through "
                "run_audit_fanout(); only PRAgent is supported here."
            )

        async with agent as a:
            response = await a.chat(Prompt)
            text = await response.text()
            return text

    tools_list.append(invoke_subagent)
    return OpenRouterAgent(
        system_instructions=system_prompt,
        tools=tools_list,
        model="openai/gpt-5-nano",
    )
