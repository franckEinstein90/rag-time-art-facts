"""Shared helpers for reading/writing the job application settings SQLite database."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent / "job_application_settings.sqlite3"


def load_user_profile() -> dict[str, str]:
    """Return user.* settings as a dict, omitting blank values."""
    if not _DB_PATH.exists():
        return {}
    with sqlite3.connect(_DB_PATH) as conn:
        rows = conn.execute(
            "SELECT key, value FROM app_settings WHERE key LIKE 'user.%'"
        ).fetchall()
    return {k: v for k, v in rows if v and v.strip()}


def save_user_profile(values: dict[str, str]) -> None:
    """Upsert user profile key/value pairs."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executemany(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                           updated_at = excluded.updated_at
            """,
            [(k, v, now) for k, v in values.items()],
        )
        conn.commit()
