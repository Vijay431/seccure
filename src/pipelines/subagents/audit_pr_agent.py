"""AuditPRAgent — fetches and processes open Dependabot pull requests.

Narrow context: only sees the pulls API response.
Writes a validated PRSummary to shared state.
"""

from __future__ import annotations

from collections.abc import Callable

from src.config.config import PRSummary, RunLimits
from src.lib.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from src.utils.github_pulls import list_dependabot_prs

_PROMPT = """You are the AuditPRAgent for the Seccure security automation system.

You MUST follow these steps exactly:
1. CALL `list_dependabot_prs()` tool to fetch all open PRs by dependabot[bot].
2. STOP and wait for the tool output. Do NOT hallucinate data.
3. Once you receive the tool output, extract the data.
4. Return the data adhering to the PRSummary schema as your final output.
   - "summarization": A brief summary of the PRs found. If no PRs, state "No open Dependabot PRs found".
   - "action_required": A boolean (true if there are PRs needing fixes, false otherwise).
   Example: {"items": [...], "count": N, "summarization": "...", "action_required": true/false}
"""


def build_audit_pr_agent(tools: list[Callable] | None = None) -> OpenRouterAgent:
    """Build and return the AuditPRAgent instance."""
    if tools is None:
        tools = [list_dependabot_prs]

    return OpenRouterAgent(
        system_instructions=_PROMPT,
        tools=tools,
        response_schema=PRSummary,
        model="openai/gpt-4o-mini",
        max_tool_calls=RunLimits.SUBAGENT_MAX_TOOL_CALLS,
    )
