import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

def _db_path() -> Path:
    """Return the path to the SQLite database file."""
    base_dir = os.environ.get("GITHUB_WORKSPACE", "/tmp")
    return Path(base_dir) / "seccure_memory.db"

def init_db() -> None:
    """Initialize the SQLite database for storing past actions."""
    path = _db_path()
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            details TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def log_action(action_type: str, details: Dict[str, Any]) -> str:
    """Log an action to the database.
    
    Args:
        action_type: Category of the action (e.g., 'fix_attempt', 'pipeline_failure', 'pr_created').
        details: A dictionary containing the action details.
        
    Returns:
        Confirmation string.
    """
    run_id = os.environ.get("GITHUB_RUN_ID", "local-run")
    path = _db_path()
    if not path.exists():
        init_db()
        
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cursor.execute(
        'INSERT INTO actions (run_id, timestamp, action_type, details) VALUES (?, ?, ?, ?)',
        (run_id, timestamp, action_type, json.dumps(details))
    )
    conn.commit()
    conn.close()
    return f"Logged action '{action_type}' successfully."

def query_past_actions(action_type: str = None, limit: int = 10) -> str:
    """Query past actions from the database to inform future decisions.
    
    Args:
        action_type: Optional filter by action_type.
        limit: Maximum number of records to return.
        
    Returns:
        JSON string of the past actions.
    """
    path = _db_path()
    if not path.exists():
        return json.dumps({"error": "Database not found. No past actions available."})
        
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if action_type:
        cursor.execute(
            'SELECT run_id, timestamp, action_type, details FROM actions WHERE action_type = ? ORDER BY id DESC LIMIT ?',
            (action_type, limit)
        )
    else:
        cursor.execute(
            'SELECT run_id, timestamp, action_type, details FROM actions ORDER BY id DESC LIMIT ?',
            (limit,)
        )
        
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        results.append({
            "run_id": row["run_id"],
            "timestamp": row["timestamp"],
            "action_type": row["action_type"],
            "details": json.loads(row["details"])
        })
        
    return json.dumps(results, indent=2)
