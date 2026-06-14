"""Coordinator agent builder.

Assembles the Coordinator with all tools, policies, and hooks.
The system prompt is passed in dynamically from main.py so that
repo-specific constraints can be injected at runtime.
"""

from __future__ import annotations

from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

from agent.coordinator.hooks import FallbackHook, MaxIterationsHook
from agent.state import read_state, write_state_section
from agent.tools.git_tools import (
    apply_package_override,
    bump_package_version,
    check_remaining_vulnerabilities,
    clone_repo,
    commit_changes,
    create_fix_branch,
    ensure_lockfile,
    push_branch,
    run_auto_fix,
)
from agent.tools.github_write import (
    add_labels,
    check_existing_seccure_pr,
    close_seccure_pr,
    create_conflict_issue,
    create_pull_request,
    get_default_branch,
)
from agent.tools.github_read import fetch_ci_logs_for_pr
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
        run_auto_fix,
        apply_package_override,
        bump_package_version,
        check_remaining_vulnerabilities,
        commit_changes,
        push_branch,
        # GitHub write operations
        create_pull_request,
        add_labels,
        create_conflict_issue,
        fetch_ci_logs_for_pr,
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

    provider = os.environ.get("LLM_PROVIDER", "antigravity").lower()
    if provider == "openrouter":
        from agent.openrouter_runner import OpenRouterAgent
        from agent.subagents.issue_agent import build_issue_agent
        from agent.subagents.pr_agent import build_pr_agent
        from agent.subagents.security_agent import build_security_agent
        
        async def invoke_subagent(TypeName: str, Role: str, Prompt: str) -> str:
            if TypeName == "IssueAgent":
                from agent.subagents.issue_agent import build_issue_agent
                agent = build_issue_agent()
            elif TypeName == "PRAgent":
                from agent.subagents.pr_agent import build_pr_agent
                agent = build_pr_agent()
            elif TypeName == "SecurityAgent":
                from agent.subagents.security_agent import build_security_agent
                agent = build_security_agent()
            else:
                return "Error: Unknown TypeName"
                
            async with agent as a:
                response = await a.chat(Prompt)
                text = await response.text()
                
                try:
                    import json
                    from agent.state import write_state_section
                    data = json.loads(text)
                    if TypeName == "IssueAgent":
                        write_state_section("security_issues", data)
                    elif TypeName == "PRAgent":
                        write_state_section("dependabot_prs", data)
                    elif TypeName == "SecurityAgent":
                        write_state_section("alerts", data)
                except Exception as e:
                    pass
                    
                return text
                
        tools_list.append(invoke_subagent)
        return OpenRouterAgent(
            system_instructions=system_prompt,
            tools=tools_list,
            model="openai/gpt-5-nano",
        )

    config = LocalAgentConfig(
        system_instructions=system_prompt,
        tools=tools_list,
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True,  # required for spawning IssueAgent / PRAgent / SecurityAgent
        ),
        policies=[policy.allow_all()],  # unattended CI — no interactive user to confirm
        save_dir="/tmp/seccure_conversations/",
        app_data_dir="/tmp/seccure_app_data/",
        hooks=[FallbackHook(), MaxIterationsHook()],
    )
    return Agent(config)

