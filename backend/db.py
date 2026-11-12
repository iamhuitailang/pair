"""SQLite 持久化层（标准库 sqlite3，单写者线程安全）。"""
import json
import sqlite3
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "crawler.db"

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_url TEXT NOT NULL,
    allowed_domain TEXT NOT NULL DEFAULT '',
    title_selector TEXT NOT NULL DEFAULT '',
    content_selector TEXT NOT NULL DEFAULT '',
    time_selector TEXT NOT NULL DEFAULT '',
    next_selector TEXT NOT NULL DEFAULT '',
    link_scope TEXT NOT NULL DEFAULT 'all',
    max_pages INTEGER NOT NULL DEFAULT 200,
    max_depth INTEGER NOT NULL DEFAULT 5,
    delay_seconds REAL NOT NULL DEFAULT 0.5,
    timeout_seconds REAL NOT NULL DEFAULT 10,
    max_retries INTEGER NOT NULL DEFAULT 2,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL REFERENCES rules(id),
    status TEXT NOT NULL DEFAULT 'pending',
    queued_count INTEGER NOT NULL DEFAULT 0,
    processing_count INTEGER NOT NULL DEFAULT 0,
    done_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    modified_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    disappeared_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    started_at REAL,
    finished_at REAL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    rule_id INTEGER NOT NULL REFERENCES rules(id),
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    updated_at_text TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    http_status INTEGER,
    depth INTEGER NOT NULL DEFAULT 0,
    fetched_at REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_pages_run ON pages(run_id);
CREATE INDEX IF NOT EXISTS idx_pages_rule_url ON pages(rule_id, url);
"""


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.executescript(SCHEMA)


def query(sql, params=()):
    with _lock, _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    with _lock, _connect() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


# ---------- rules ----------

def create_rule(data: dict) -> dict:
    fields = (
        "name", "start_url", "allowed_domain", "title_selector", "content_selector",
        "time_selector", "next_selector", "link_scope", "max_pages", "max_depth",
        "delay_seconds", "timeout_seconds", "max_retries", "enabled",
    )
    values = [data.get(f) for f in fields]
    rid = execute(
        f"INSERT INTO rules ({','.join(fields)}, created_at) VALUES ({','.join('?' * len(fields))}, ?)",
        values + [time.time()],
    )
    return get_rule(rid)


def get_rule(rule_id: int):
    return query_one("SELECT * FROM rules WHERE id = ?", (rule_id,))


def list_rules():
    return query("SELECT * FROM rules ORDER BY id")


def update_rule(rule_id: int, data: dict) -> dict:
    fields = (
        "name", "start_url", "allowed_domain", "title_selector", "content_selector",
        "time_selector", "next_selector", "link_scope", "max_pages", "max_depth",
        "delay_seconds", "timeout_seconds", "max_retries", "enabled",
    )
    sets, params = [], []
    for f in fields:
        if f in data and data[f] is not None:
            sets.append(f"{f} = ?")
            params.append(data[f])
    if sets:
        params.append(rule_id)
        execute(f"UPDATE rules SET {', '.join(sets)} WHERE id = ?", params)
    return get_rule(rule_id)


def delete_rule(rule_id: int):
    execute("DELETE FROM rules WHERE id = ?", (rule_id,))


# ---------- runs ----------

def create_run(rule_id: int) -> dict:
    rid = execute(
        "INSERT INTO runs (rule_id, status) VALUES (?, 'pending')", (rule_id,)
    )
    return get_run(rid)


def get_run(run_id: int):
    return query_one("SELECT * FROM runs WHERE id = ?", (run_id,))


def list_runs(rule_id=None):
    if rule_id:
        return query(
            "SELECT r.*, ru.name AS rule_name FROM runs r JOIN rules ru ON ru.id = r.rule_id "
            "WHERE r.rule_id = ? ORDER BY r.id DESC", (rule_id,))
    return query(
        "SELECT r.*, ru.name AS rule_name FROM runs r JOIN rules ru ON ru.id = r.rule_id "
        "ORDER BY r.id DESC LIMIT 100")


def update_run(run_id: int, **fields):
    sets = ", ".join(f"{k} = ?" for k in fields)
    execute(f"UPDATE runs SET {sets} WHERE id = ?", list(fields.values()) + [run_id])


def incr_run(run_id: int, **counters):
    sets = ", ".join(f"{k} = {k} + ?" for k in counters)
    execute(f"UPDATE runs SET {sets} WHERE id = ?", list(counters.values()) + [run_id])


def previous_finished_run(rule_id: int, before_run_id: int):
    return query_one(
        "SELECT * FROM runs WHERE rule_id = ? AND id < ? AND status = 'finished' "
        "ORDER BY id DESC LIMIT 1", (rule_id, before_run_id))


def latest_finished_run(rule_id: int):
    return query_one(
        "SELECT * FROM runs WHERE rule_id = ? AND status = 'finished' "
        "ORDER BY id DESC LIMIT 1", (rule_id,))


# ---------- pages ----------

def insert_page(page: dict):
    execute(
        "INSERT INTO pages (run_id, rule_id, url, title, content, updated_at_text, "
        "content_hash, status, http_status, depth, fetched_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (page["run_id"], page["rule_id"], page["url"], page.get("title", ""),
         page.get("content", ""), page.get("updated_at_text", ""),
         page.get("content_hash", ""), page["status"], page.get("http_status"),
         page.get("depth", 0), page.get("fetched_at", time.time())),
    )


def pages_of_run(run_id: int, status=None):
    if status:
        return query("SELECT * FROM pages WHERE run_id = ? AND status = ? ORDER BY id",
                     (run_id, status))
    return query("SELECT * FROM pages WHERE run_id = ? ORDER BY id", (run_id,))


def pages_map_of_run(run_id: int):
    return {p["url"]: p for p in pages_of_run(run_id)}


def get_page(page_id: int):
    return query_one("SELECT * FROM pages WHERE id = ?", (page_id,))


def find_page_in_run(run_id: int, url: str):
    return query_one("SELECT * FROM pages WHERE run_id = ? AND url = ?", (run_id, url))
