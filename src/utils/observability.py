"""Observability helpers — Actions Job Summary and token usage logging."""

from __future__ import annotations

import os
from typing import Any


def log_token_usage(usage_map: dict[str, Any], extra_summary: str = "") -> str:
    """Write a token usage summary table to the GitHub Actions Job Summary.

    Args:
        usage_map: Dict mapping agent name to token count dict
                   {prompt_token_count, candidates_token_count,
                    thoughts_token_count, total_token_count}.
        extra_summary: Optional extra markdown to append (e.g. fix stats).

    Returns:
        Confirmation message.
    """
    from datetime import date

    today = date.today().isoformat()
    rows = []
    grand_prompt = grand_output = grand_thinking = grand_total = 0

    for agent_name, counts in usage_map.items():
        prompt = counts.get("prompt_token_count", 0)
        output = counts.get("candidates_token_count", 0)
        thinking = counts.get("thoughts_token_count", 0)
        total = counts.get("total_token_count", 0)
        grand_prompt += prompt
        grand_output += output
        grand_thinking += thinking
        grand_total += total
        rows.append(
            f"| {agent_name} | {prompt:,} | {output:,} | {thinking:,} | {total:,} |"
        )

    rows.append(
        f"| **Total** | **{grand_prompt:,}** | **{grand_output:,}** "
        f"| **{grand_thinking:,}** | **{grand_total:,}** |"
    )

    constraints_dir = os.environ.get("SECCURE_CONSTRAINTS_DIR", "")
    constraints_note = ""
    if constraints_dir:
        from pathlib import Path

        cf = Path(constraints_dir) / "constraints.md"
        if cf.exists():
            constraints_note = (
                "\n**Constraints active:** Yes — `.seccure/constraints.md`"
            )

    markdown = (
        f"""## 🛡️ Seccure Run Summary — {today}
{constraints_note}

### Token Usage
| Agent | Prompt Tokens | Output Tokens | Thinking Tokens | Total |
|-------|-------------|--------------|----------------|-------|
"""
        + "\n".join(rows)
        + "\n"
    )

    if extra_summary:
        markdown += f"\n{extra_summary}\n"

    return _write_to_summary(markdown)


def _write_to_summary(markdown: str) -> str:
    """Append markdown to GITHUB_STEP_SUMMARY. Falls back to stdout."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(markdown + "\n")
        return "Job summary updated."
    print(markdown)
    return "No GITHUB_STEP_SUMMARY set — printed to stdout."
