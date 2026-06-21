"""AuditIssueAgent — fetches and processes GitHub security/dependabot issues.

Narrow context: only sees the issues API response.
Writes a validated IssueSummary to shared state.
"""

from __future__ import annotations

from collections.abc import Callable

from src.config.config import IssueSummary, RunLimits
from src.lib.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from src.lib.state import read_state, write_state_section
from src.utils.github_issues import list_security_issues

_PROMPT = """You are the AuditIssueAgent for the Seccure security automation system.

You MUST follow these steps exactly:
1. CALL `list_security_issues()` tool to fetch open security issues.
2. STOP and wait for the tool output. Do NOT hallucinate data.
3. Once you receive the tool output, extract the data.
4. CALL `write_state_section()` tool with section="security_issues" and
   the extracted data.
5. Output the EXACT SAME JSON structure with the addition of:
   - "summarization": A brief summary of the issues found. If no issues, state "No security issues found".
   - "action_required": A boolean (true if there are issues needing fixes, false otherwise).
   Example: {"items": [...], "count": N, "summarization": "...", "action_required": true/false}
"""


def build_audit_issue_agent(tools: list[Callable] | None = None) -> OpenRouterAgent:
    """Build and return the AuditIssueAgent instance."""
    if tools is None:
        tools = [list_security_issues, read_state, write_state_section]

    return OpenRouterAgent(
        system_instructions=_PROMPT,
        tools=tools,
        response_schema=IssueSummary,
        model="openai/gpt-4o-mini",
        max_tool_calls=RunLimits.SUBAGENT_MAX_TOOL_CALLS,
    )
