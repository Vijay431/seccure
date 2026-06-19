"""Deterministic coordinator helpers."""

from __future__ import annotations

from agent.config import ToolResult


def should_exit_for_tool_result(result: ToolResult) -> bool:
    """Return true when a tool result must stop the coordinator immediately."""

    return result.fatal
