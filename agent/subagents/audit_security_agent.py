"""AuditSecurityAgent — fetches and deduplicates npm Dependabot + code scanning alerts.

Narrow context: only sees security alert API responses.
Writes a validated AlertSummary to shared state.
"""

from __future__ import annotations

from agent.config import AlertSummary, RunLimits
from agent.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from agent.state import read_state, write_state_section
from agent.tools.github_security import list_code_scanning_alerts, list_dependabot_alerts

_PROMPT = """You are the AuditSecurityAgent for the Seccure security automation system.

You MUST follow these steps exactly:
1. CALL `list_dependabot_alerts()` and `list_code_scanning_alerts()` tools.
2. STOP and wait for the tools' output. Do NOT hallucinate data.
3. Once you receive the output, combine the lists.
4. CALL `write_state_section()` tool with section="alerts" and the extracted data.
5. Output the EXACT SAME JSON:
   {"items": [...], "count": N, "critical_count": X, "high_count": Y}
"""


def build_audit_security_agent() -> OpenRouterAgent:
    """Build and return the AuditSecurityAgent instance."""
    tools = [
        list_dependabot_alerts,
        list_code_scanning_alerts,
        read_state,
        write_state_section,
    ]

    return OpenRouterAgent(
        system_instructions=_PROMPT,
        tools=tools,
        response_schema=AlertSummary,
        model="openai/gpt-4o-mini",
        max_tool_calls=RunLimits.SUBAGENT_MAX_TOOL_CALLS,
    )
