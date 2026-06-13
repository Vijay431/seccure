"""PRAgent — fetches and processes open Dependabot pull requests.

Narrow context: only sees the pulls API response.
Writes a validated PRSummary to shared state.
"""

from __future__ import annotations

from google.antigravity import Agent, LocalAgentConfig

from agent.config import PRSummary
from agent.state import read_state, write_state_section
from agent.tools.github_read import list_dependabot_prs

_PROMPT = """You are the PRAgent for the Seccure security automation system.

Your ONLY job:
1. Call list_dependabot_prs() to fetch all open PRs by dependabot[bot].
2. For each PR extract: pr_number (from 'number' field), package, from_version, to_version, url (from 'html_url' field).
   If package/versions are 'unknown', keep them as-is.
3. Call write_state_section('dependabot_prs', <list of PR dicts>) to persist.
4. Respond with ONLY valid JSON matching PRSummary: {"items": [...], "count": N}

Do NOT call any other tools. Do NOT generate prose."""


def build_pr_agent() -> Agent:
    """Build and return the PRAgent instance."""
    config = LocalAgentConfig(
        system_instructions=_PROMPT,
        tools=[list_dependabot_prs, read_state, write_state_section],
        response_schema=PRSummary,
    )
    return Agent(config)
