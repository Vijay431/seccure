"""IssueAgent — fetches and processes GitHub security/dependabot issues.

Narrow context: only sees the issues API response.
Writes a validated IssueSummary to shared state.
"""

from __future__ import annotations

from google.antigravity import Agent, LocalAgentConfig

from agent.config import IssueSummary
from agent.state import read_state, write_state_section
from agent.tools.github_read import list_security_issues

_PROMPT = """You are the IssueAgent for the Seccure security automation system.

Your ONLY job:
1. Call list_security_issues() to fetch all open issues labelled 'security' or 'dependabot'.
2. For each issue extract: issue_number (from 'number' field), title, labels (list of name strings), url (from 'html_url' field).
3. Call write_state_section('security_issues', <list of issue dicts>) to persist.
4. Respond with ONLY valid JSON matching IssueSummary: {"items": [...], "count": N}

Do NOT call any other tools. Do NOT generate prose."""


def build_issue_agent() -> Agent:
    """Build and return the IssueAgent instance."""
    config = LocalAgentConfig(
        system_instructions=_PROMPT,
        tools=[list_security_issues, read_state, write_state_section],
        response_schema=IssueSummary,
    )
    return Agent(config)
