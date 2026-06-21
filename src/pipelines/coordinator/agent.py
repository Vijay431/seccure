"""Coordinator agent builder.

Assembles the Coordinator with all tools, policies, and hooks.
The system prompt is passed in dynamically from main.py so that
repo-specific constraints can be injected at runtime.
"""

from __future__ import annotations

from src.lib.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from src.lib.state import read_state, write_state_section
from src.pipelines.subagents.audit_fanout import run_audit_fanout
from src.utils.git_tools import (
    apply_package_override,
    bump_package_version,
    check_remaining_vulnerabilities,
    clone_repo,
    ensure_lockfile,
    run_auto_fix,
)
from src.utils.github_issues import create_conflict_issue
from src.utils.github_pulls import (
    check_existing_seccure_pr,
    close_seccure_pr,
    fetch_ci_logs_for_pr,
    get_default_branch,
)
from src.utils.observability import log_token_usage
from src.utils.repo_constraints import read_repo_constraints


def build_coordinator(system_prompt: str) -> OpenRouterAgent:
    """Build and return the Coordinator agent instance.

    Args:
        system_prompt: Dynamically assembled system prompt
                       (base prompt + optional repo constraints).

    Returns:
        Configured OpenRouter agent ready to be used as an async context manager.
    """
    from src.config.config import ToolResult

    async def run_audit_fanout_and_save() -> ToolResult:
        """Run the three audit sources concurrently and save results to state."""
        res = await run_audit_fanout()
        if res.ok and res.data and isinstance(res.data, dict):
            write_state_section(
                "security_issues", res.data.get("security_issues", {}).get("items", [])
            )
            write_state_section(
                "dependabot_prs", res.data.get("dependabot_prs", {}).get("items", [])
            )
            write_state_section("alerts", res.data.get("alerts", {}).get("items", []))
        return res

    tools_list = [
        # Shared state
        read_state,
        write_state_section,
        run_audit_fanout_and_save,
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

            tools_list = [traceable(t) if callable(t) else t for t in tools_list]  # type: ignore
        except ImportError:
            print("[Seccure] Warning: langsmith not installed. Skipping tracing.")

    async def invoke_subagent(TypeName: str, Role: str, Prompt: str) -> str:
        if TypeName == "PRAgent":
            from src.pipelines.subagents.pr_agent import build_pr_agent

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

    class CoordinatorAgent(OpenRouterAgent):
        async def chat(self, prompt: str):
            try:
                return await super().chat(prompt)
            except Exception as e:
                import os
                import subprocess

                from src.lib.state import write_state_section

                print(f"[Seccure] Exception caught during coordinator execution: {e}")
                print(
                    "[Seccure] Performing secure teardown (git reset --hard, git clean -fd)"
                )
                try:
                    subprocess.run(["git", "reset", "--hard"], check=False)
                    subprocess.run(["git", "clean", "-fd"], check=False)
                except Exception as teardown_err:
                    print(f"[Seccure] Teardown failed: {teardown_err}")

                summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
                if summary_file:
                    try:
                        with open(summary_file, "a") as f:
                            f.write(
                                f"\n## 🚨 Seccure Agent Failed\n\n**Error**: `{str(e)}`\n\nPerformed secure teardown of the workspace.\n"
                            )
                    except Exception:
                        pass

                try:
                    write_state_section("status", "error")
                    write_state_section("errors", [str(e)])
                except Exception:
                    pass

                raise e

    tools_list.append(invoke_subagent)
    return CoordinatorAgent(
        system_instructions=system_prompt,
        tools=tools_list,
        model="openai/gpt-5-nano",
    )
