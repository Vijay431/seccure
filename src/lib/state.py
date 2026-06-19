"""Shared state read/write helpers used as ADK tool functions.

All agents share read_state() and write_state_section() to coordinate via
a single JSON file on disk: /tmp/seccure_state_{run_id}.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.config.config import SeccureState


def _state_path(run_id: str) -> Path:
    base_dir = os.environ.get("GITHUB_WORKSPACE", "/tmp")
    return Path(base_dir) / f"seccure_state_{run_id}.json"


def _get_run_id() -> str:
    return os.environ["GITHUB_RUN_ID"]


# ---------------------------------------------------------------------------
# ADK tool functions (shared by all agents)
# ---------------------------------------------------------------------------


def read_state() -> str:
    """Read the current SeccureState from disk and return it as a JSON string.

    Returns:
        JSON string of the full SeccureState object, or an error dict.
    """
    path = _state_path(_get_run_id())
    if not path.exists():
        return json.dumps({"error": "State file not found", "path": str(path)})
    return path.read_text()


def write_state_section(section: str, data: Any) -> str:
    """Write a single top-level section of SeccureState to disk.

    Args:
        section: The field name on SeccureState to update
                 (e.g. 'alerts', 'fix_results', 'status').
        data: The new value. Must be JSON-serialisable.

    Returns:
        Confirmation message or error string.
    """
    path = _state_path(_get_run_id())
    if not path.exists():
        return f"Error: state file {path} not found"
    raw = json.loads(path.read_text())
    raw[section] = data
    path.write_text(json.dumps(raw, indent=2))
    return f"State section '{section}' updated successfully."


# ---------------------------------------------------------------------------
# Internal helpers (used by main.py, not exposed as ADK tools)
# ---------------------------------------------------------------------------


def init_state(state: SeccureState) -> None:
    """Initialise and persist a brand-new SeccureState to disk."""
    path = _state_path(state.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2))


def load_state() -> SeccureState:
    """Load and validate SeccureState from disk into a typed model."""
    path = _state_path(_get_run_id())
    return SeccureState.model_validate_json(path.read_text())
