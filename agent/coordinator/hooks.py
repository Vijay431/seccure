"""ADK lifecycle hooks for the Coordinator agent."""

from __future__ import annotations

import subprocess
from typing import Any

import httpx
from google.antigravity.hooks import hooks


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
