from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent / "job_application_settings.sqlite3"
)


def create_job_application_settings_db(db_path: str | Path) -> Path:
    """Create the SQLite database used for job application analyzer settings."""
    path = Path(db_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_storage_path TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO app_state (id, last_storage_path, updated_at)
            VALUES (1, ?, ?);
            """,
            (str(Path.home()), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the SQLite settings database for the job application analyzer."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    created_path = create_job_application_settings_db(args.db_path)
    print(created_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
