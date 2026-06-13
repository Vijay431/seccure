"""SecurityAgent — fetches and deduplicates npm Dependabot + code scanning alerts.

Narrow context: only sees security alert API responses.
Writes a validated AlertSummary to shared state.
"""

from __future__ import annotations

from google.antigravity import Agent, LocalAgentConfig

from agent.config import AlertSummary
from agent.state import read_state, write_state_section
from agent.tools.github_read import list_code_scanning_alerts, list_dependabot_alerts

_PROMPT = """You are the SecurityAgent for the Seccure security automation system.

Your ONLY job:
1. Call list_dependabot_alerts() to fetch all open npm Dependabot alerts.
2. Call list_code_scanning_alerts() to fetch open code scanning alerts.
3. Merge and deduplicate both lists by cve_id. For each unique alert extract:
   alert_number, cve_id, package, severity, patched_version (nullable), advisory_url.
4. Call write_state_section('alerts', <list of alert dicts>) to persist.
5. Count critical_count (severity='critical') and high_count (severity='high').
6. Respond with ONLY valid JSON matching AlertSummary:
   {"items": [...], "count": N, "critical_count": N, "high_count": N}

Do NOT call any other tools. Do NOT generate prose."""


def build_security_agent() -> Agent:
    """Build and return the SecurityAgent instance."""
    config = LocalAgentConfig(
        system_instructions=_PROMPT,
        tools=[
            list_dependabot_alerts,
            list_code_scanning_alerts,
            read_state,
            write_state_section,
        ],
        response_schema=AlertSummary,
    )
    return Agent(config)
