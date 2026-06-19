"""AuditPRAgent — fetches and processes open Dependabot pull requests.

Narrow context: only sees the pulls API response.
Writes a validated PRSummary to shared state.
"""

from __future__ import annotations

from agent.config import PRSummary, RunLimits
from agent.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from agent.state import read_state, write_state_section
from agent.tools.github_read import list_dependabot_prs

_PROMPT = """You are the AuditPRAgent for the Seccure security automation system.

You MUST follow these steps exactly:
1. CALL `list_dependabot_prs()` tool to fetch all open PRs by dependabot[bot].
2. STOP and wait for the tool output. Do NOT hallucinate data.
3. Once you receive the tool output, extract the data.
4. CALL `write_state_section()` tool with section="dependabot_prs" and
   the extracted data.
5. Output the EXACT SAME JSON: {"items": [...], "count": N}
"""


def build_audit_pr_agent() -> OpenRouterAgent:
    """Build and return the AuditPRAgent instance."""
    tools = [list_dependabot_prs, read_state, write_state_section]

    return OpenRouterAgent(
        system_instructions=_PROMPT,
        tools=tools,
        response_schema=PRSummary,
        model="openai/gpt-4o-mini",
        max_tool_calls=RunLimits.SUBAGENT_MAX_TOOL_CALLS,
    )
