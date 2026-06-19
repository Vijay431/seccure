"""Redacted agent event logging."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"x-access-token:[^@\\s]+@"),
    re.compile(r"(?i)(api[_-]?key|token|secret)(['\"]?\\s*[:=]\\s*['\"]?)[^'\"\\s,}]+"),
]


def redact_text(text: str) -> str:
    """Redact tokens and API keys from event output."""

    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(_redact_match, redacted)
    return redacted


def _redact_match(match: re.Match[str]) -> str:
    value = match.group(0)
    if "x-access-token:" in value:
        return value.split(":")[0] + ":[REDACTED]@"
    return "[REDACTED]"


def write_agent_event(
    path: str | Path,
    agent: str,
    event: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append one redacted JSONL event and mirror a concise line to stdout."""

    event_payload = {
        "ts": datetime.now(UTC).isoformat(),
        "agent": agent,
        "event": event,
        "payload": payload or {},
    }
    line = redact_text(json.dumps(event_payload, sort_keys=True))
    print(f"[Seccure:{agent}] {redact_text(event)}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
