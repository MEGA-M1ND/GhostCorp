"""
core/persistence.py — SQLite persistence for SimCorp (MVP).

Each completed quarter is appended to the `ticks` table as a full JSON snapshot
of the state. This gives us both durability (state survives a restart) and a
queryable history, without a server. The DB file lives in db/ (gitignored).
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

from core.state import SimCorpState

# Resolve the DB path from DATABASE_URL (sqlite:///./db/simcorp.db) with a sane
# default. We only support the sqlite scheme for the MVP.
_DEFAULT_PATH = os.path.join("db", "simcorp.db")


def _db_path() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return _DEFAULT_PATH


def _connect() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the ticks table if it doesn't exist."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ticks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario   TEXT    NOT NULL,
                quarter    INTEGER NOT NULL,
                ts         TEXT    NOT NULL,
                state_json TEXT    NOT NULL
            )
            """
        )
        conn.commit()


def persist_to_sqlite(state: SimCorpState) -> None:
    """Append the current state as a snapshot row."""
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO ticks (scenario, quarter, ts, state_json) VALUES (?, ?, ?, ?)",
            (
                state["scenario"],
                state["quarter"],
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                json.dumps(state),
            ),
        )
        conn.commit()


def load_latest_state() -> SimCorpState | None:
    """Return the most recently persisted state, or None if the DB is empty."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT state_json FROM ticks ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return json.loads(row["state_json"]) if row else None


def reset_db() -> None:
    """Clear all persisted ticks (used by the /reset endpoint)."""
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM ticks")
        conn.commit()
