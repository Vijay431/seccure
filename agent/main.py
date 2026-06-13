#!/usr/bin/env python3
"""Seccure Agent entrypoint.

Reads repo-specific constraints, initialises shared state, builds the
Coordinator agent, and runs it to completion (one-shot, unattended CI).

Environment variables required:
    GITHUB_RUN_ID         GitHub Actions run ID (unique per run)
    GITHUB_TOKEN          GitHub token for API calls and git auth
    GEMINI_API_KEY        Gemini API key for ADK agent model access

Environment variables optional:
    TARGET_REPO              Target repository in 'owner/repo' format (defaults to GITHUB_REPOSITORY)
    SECCURE_CONSTRAINTS_DIR  Path to directory containing constraints.md
    ADDITIONAL_CONSTRAINTS   One-off constraints from workflow_dispatch input
"""

from __future__ import annotations

import asyncio
import os
from datetime import date
from pathlib import Path

import sys
from dotenv import load_dotenv

load_dotenv()

# Ensure the root directory is in sys.path so 'agent' module can be found
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from agent.config import SeccureState
from agent.coordinator.agent import build_coordinator
from agent.state import init_state
from agent.tools.repo_constraints import load_constraints_text

_BASE_PROMPT_PATH = Path(__file__).parent / "coordinator" / "prompt.md"


def _build_system_prompt(constraints: str) -> str:
    """Combine the base coordinator prompt with optional repo constraints.

    Args:
        constraints: Combined text from .seccure/constraints.md and
                     ADDITIONAL_CONSTRAINTS env var. Empty string = no constraints.

    Returns:
        Full system prompt string to pass to the Coordinator agent.
    """
    base = _BASE_PROMPT_PATH.read_text()
    if not constraints.strip():
        return base

    return f"""{base}

---
## ⚠️ Repo-Specific Constraints (MUST be followed)

The following constraints have been set by the target repository's maintainers.
They override your default fix strategy where applicable.
Do NOT violate these constraints under any circumstances.
If a constraint prevents you from fixing a vulnerability, create a conflict
issue with the reason: "blocked by repo constraint: <quote the relevant rule>".

{constraints}
---
"""


def _trace_if_enabled(func):
    import os
    if os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        try:
            from langsmith import traceable
            return traceable(run_type="chain", name="SeccureAgentRun")(func)
        except ImportError:
            pass
    return func

@_trace_if_enabled
async def main() -> None:
    """Main entrypoint — initialise state and run the Coordinator."""
    run_id = os.environ["GITHUB_RUN_ID"]
    repo = os.environ.get("TARGET_REPO") or os.environ["GITHUB_REPOSITORY"]
    today = date.today().strftime("%Y%m%d")
    fix_branch = f"seccure/auto-fix-{today}"

    print(f"[Seccure] Starting run {run_id} for repo: {repo}")
    print(f"[Seccure] Fix branch: {fix_branch}")

    # 1. Load repo-specific constraints (may be empty string)
    constraints = load_constraints_text()
    if constraints:
        print("[Seccure] Repo constraints loaded — will be injected into Coordinator prompt.")
    else:
        print("[Seccure] No repo constraints found — running with default behaviour.")

    # 2. Initialise shared state on disk
    state = SeccureState(
        run_id=run_id,
        repo=repo,
        fix_branch=fix_branch,
        constraints=constraints,
    )
    init_state(state)
    from agent.state import _state_path
    print(f"[Seccure] State initialised at {_state_path(run_id)}")

    # 3. Build Coordinator with dynamically injected constraints
    system_prompt = _build_system_prompt(constraints)
    coordinator = build_coordinator(system_prompt)

    task_prompt = f"""
You are the Seccure Coordinator. Your job is to:
1. Spawn IssueAgent, PRAgent, and SecurityAgent in parallel to gather security data.
2. Read the shared state summary.
3. If there is nothing to fix, exit cleanly with status 'nothing_to_fix'.
4. Otherwise, clone the target repo, apply npm vulnerability fixes, and open a consolidated PR.

Target repository: {repo}
Run ID: {run_id}
Fix branch: {fix_branch}

Begin now. Follow your system instructions exactly.
"""

    # 4. Run the Coordinator
    async with coordinator as agent:
        response = await agent.chat(task_prompt)
        final_text = await response.text()
        print(f"\n[Seccure] Coordinator completed:\n{final_text}")

        # 5. Capture and report token usage
        usage = agent.conversation.total_usage
        print(
            f"\n[Seccure] Coordinator token usage — "
            f"prompt: {usage.prompt_token_count:,} | "
            f"output: {usage.candidates_token_count:,} | "
            f"thinking: {usage.thoughts_token_count:,} | "
            f"total: {usage.total_token_count:,}"
        )


if __name__ == "__main__":
    asyncio.run(main())
