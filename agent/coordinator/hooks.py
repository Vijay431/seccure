"""ADK lifecycle hooks for the Coordinator agent."""

from __future__ import annotations

import subprocess
from typing import Any

import httpx
from google.antigravity.hooks import hooks
from google.antigravity.hooks.hooks import HookContext, HookResult

from agent.config import RunLimits


class MaxIterationsHook(hooks.PreToolCallDecideHook):
    """Blocks further tool calls once the coordinator hits its call budget.

    Uses the ADK's ``PreToolCallDecideHook`` so the framework itself prevents
    the call rather than the agent crashing mid-flight.  Returning
    ``HookResult(allow=False)`` causes the ADK to surface the ``message`` back
    to the model, giving it a chance to emit a graceful final response instead
    of an unhandled exception.

    The limit is read from ``RunLimits.COORDINATOR_MAX_TOOL_CALLS`` which
    honours the ``SECCURE_COORDINATOR_MAX_TOOLS`` env-var.
    """

    def __init__(self) -> None:
        self._call_count: int = 0
        self._limit: int = RunLimits.COORDINATOR_MAX_TOOL_CALLS

    async def run(self, context: HookContext, data: Any) -> HookResult:  # noqa: ANN401
        self._call_count += 1
        tool_name = getattr(data, "tool_name", "?")
        print(
            f"[Seccure] Tool call #{self._call_count}/{self._limit}: {tool_name}"
        )
        if self._call_count > self._limit:
            msg = (
                f"[Seccure] MaxIterationsHook: coordinator has exceeded its "
                f"{self._limit}-tool-call budget. No further tools will be "
                f"invoked. Please emit your final summary now without calling "
                f"any more tools. Increase SECCURE_COORDINATOR_MAX_TOOLS if "
                f"this repo genuinely requires more steps."
            )
            print(msg)
            return HookResult(allow=False, message=msg)
        return HookResult(allow=True)


class FallbackHook(hooks.OnToolErrorHook):
    """Intercepts tool errors and returns structured recovery guidance.

    Allows the Coordinator to self-correct rather than crash on transient
    GitHub API errors or subprocess failures.
    """

    async def run(self, context: Any, data: Any) -> str | None:  # noqa: ANN401
        if isinstance(data, httpx.HTTPStatusError):
            code = data.response.status_code
            url = str(data.request.url)
            if code == 403:
                return (
                    f"[GitHub API 403 Forbidden — check GITHUB_TOKEN permissions "
                    f"for: {url}]"
                )
            if code == 404:
                return f"[GitHub API 404 Not Found — resource may not exist: {url}]"
            if code == 429:
                return (
                    f"[GitHub API 429 Rate Limited — too many requests, "
                    f"consider retrying later: {url}]"
                )
            return (
                f"[GitHub API {code} error at {url}: "
                f"{data.response.text[:300]}]"
            )
        if isinstance(data, subprocess.CalledProcessError):
            return (
                f"[Shell command failed (exit {data.returncode}): "
                f"{(data.stderr or '')[:400]}]"
            )
        if isinstance(data, FileNotFoundError):
            return f"[File not found: {data.filename}]"
        # Return None to let the ADK harness handle other error types
        return None
