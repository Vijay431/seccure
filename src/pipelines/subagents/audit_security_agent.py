"""AuditSecurityAgent — fetches and deduplicates npm Dependabot + code scanning alerts.

Narrow context: only sees security alert API responses.
Writes a validated AlertSummary to shared state.
"""

from __future__ import annotations

from collections.abc import Callable

from src.config.config import AlertSummary, RunLimits
from src.lib.resilient_runner import ResilientOpenRouterAgent as OpenRouterAgent
from src.utils.github_security import list_code_scanning_alerts, list_dependabot_alerts

_PROMPT = """You are the AuditSecurityAgent for the Seccure security automation system.

You MUST follow these steps exactly:
1. CALL `list_dependabot_alerts()` and `list_code_scanning_alerts()` tools.
2. STOP and wait for the tools' output. Do NOT hallucinate data.
3. Once you receive the output, combine the lists.
4. Return the data adhering to the AlertSummary schema as your final output.
   - "summarization": A brief summary of the alerts found. If no alerts, state "No security alerts found".
   - "action_required": A boolean (true if there are alerts needing fixes, false otherwise).
   Example: {"items": [...], "count": N, "critical_count": X, "high_count": Y, "summarization": "...", "action_required": true/false}
"""


def build_audit_security_agent(tools: list[Callable] | None = None) -> OpenRouterAgent:
    """Build and return the AuditSecurityAgent instance."""
    if tools is None:
        tools = [
            list_dependabot_alerts,
            list_code_scanning_alerts,
        ]

    return OpenRouterAgent(
        system_instructions=_PROMPT,
        tools=tools,
        response_schema=AlertSummary,
        model="openai/gpt-4o-mini",
        max_tool_calls=RunLimits.SUBAGENT_MAX_TOOL_CALLS,
    )
