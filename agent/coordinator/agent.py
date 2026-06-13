"""Coordinator agent builder.

Assembles the Coordinator with all tools, policies, and hooks.
The system prompt is passed in dynamically from main.py so that
repo-specific constraints can be injected at runtime.
"""

from __future__ import annotations

from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from agent.coordinator.hooks import FallbackHook
from agent.state import read_state, write_state_section
from agent.tools.git_tools import (
    apply_npm_overrides,
    bump_package_version,
    check_remaining_vulnerabilities,
    clone_repo,
    commit_changes,
    create_fix_branch,
    ensure_lockfile,
    push_branch,
    run_npm_audit_fix,
)
from agent.tools.github_write import (
    add_labels,
    check_existing_seccure_pr,
    close_seccure_pr,
    create_conflict_issue,
    create_pull_request,
    get_default_branch,
)
from agent.tools.observability import log_token_usage
from agent.tools.repo_constraints import read_repo_constraints


def build_coordinator(system_prompt: str) -> Agent:
    """Build and return the Coordinator agent instance.

    Args:
        system_prompt: Dynamically assembled system prompt
                       (base prompt + optional repo constraints).

    Returns:
        Configured ADK Agent ready to be used as an async context manager.
    """
    tools_list = [
        # Shared state
        read_state,
        write_state_section,
        # Constraints (can be re-read mid-run if needed)
        read_repo_constraints,
        # Idempotency guard
        check_existing_seccure_pr,
        close_seccure_pr,
        # Repo metadata
        get_default_branch,
        # Git / npm operations
        clone_repo,
        create_fix_branch,
        ensure_lockfile,
        run_npm_audit_fix,
        apply_npm_overrides,
        bump_package_version,
        check_remaining_vulnerabilities,
        commit_changes,
        push_branch,
        # GitHub write operations
        create_pull_request,
        add_labels,
        create_conflict_issue,
        # Observability
        log_token_usage,
    ]

    # Add LangSmith tracing to tools if enabled
    import os
    if os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        try:
            from langsmith import traceable
            tools_list = [traceable(t) if callable(t) else t for t in tools_list]
        except ImportError:
            print("[Seccure] Warning: langsmith not installed. Skipping tracing.")

    config = LocalAgentConfig(
        system_instructions=system_prompt,
        tools=tools_list,
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True,  # required for spawning IssueAgent / PRAgent / SecurityAgent
        ),
        policies=[policy.allow_all()],  # unattended CI — no interactive user to confirm
        save_dir="/tmp/seccure_conversations/",
        app_data_dir="/tmp/seccure_app_data/",
        hooks=[FallbackHook()],
    )
    return Agent(config)
