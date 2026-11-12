"""SQLite 存储层（stdlib sqlite3，无 ORM）。"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("GAME_REPLAY_DB", os.path.join(os.path.dirname(__file__), "..", "data.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id       TEXT PRIMARY KEY,
    session_id     TEXT NOT NULL,
    player_id      TEXT NOT NULL,
    event_type     TEXT NOT NULL,
    occurred_at    TEXT NOT NULL,          -- ISO8601 UTC
    sequence       INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    payload_json   TEXT NOT NULL,
    content_hash   TEXT NOT NULL,
    received_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_player_time ON events(player_id, occurred_at);

CREATE TABLE IF NOT EXISTS analysis_cache (
    session_id   TEXT NOT NULL,
    rules_version TEXT NOT NULL,
    event_count  INTEGER NOT NULL,
    result_json  TEXT NOT NULL,
    computed_at  TEXT NOT NULL,
    PRIMARY KEY (session_id, rules_version)
);
"""


def init_db(path: str | None = None) -> None:
    with get_conn(path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn(path: str | None = None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
