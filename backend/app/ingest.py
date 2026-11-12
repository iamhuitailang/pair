"""批量写入：逐条校验、幂等去重、冲突检测。"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from pydantic import ValidationError

from .db import get_conn
from .schemas import SUPPORTED_SCHEMA_VERSIONS, EventIn


def _content_hash(ev: EventIn) -> str:
    canonical = json.dumps(
        {
            "event_id": ev.event_id,
            "session_id": ev.session_id,
            "player_id": ev.player_id,
            "event_type": ev.event_type,
            "occurred_at": ev.occurred_at.astimezone(timezone.utc).isoformat(),
            "sequence": ev.sequence,
            "schema_version": ev.schema_version,
            "payload": ev.payload,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ingest_batch(raw_events: list[dict], db_path: str | None = None) -> list[dict]:
    """逐条处理一批事件，返回每条的接收结果。

    status: accepted | duplicate | rejected
    """
    results = []
    now = datetime.now(timezone.utc).isoformat()
    with get_conn(db_path) as conn:
        for raw in raw_events:
            event_id = raw.get("event_id") if isinstance(raw, dict) else None
            try:
                ev = EventIn.model_validate(raw)
            except ValidationError as e:
                first = e.errors()[0]
                loc = ".".join(str(p) for p in first["loc"])
                results.append({
                    "event_id": event_id,
                    "status": "rejected",
                    "reason": f"invalid_field:{loc}:{first['msg']}",
                })
                continue

            if ev.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
                results.append({
                    "event_id": ev.event_id,
                    "status": "rejected",
                    "reason": f"unsupported_schema_version:{ev.schema_version}",
                })
                continue

            chash = _content_hash(ev)
            try:
                conn.execute(
                    """INSERT INTO events
                       (event_id, session_id, player_id, event_type, occurred_at,
                        sequence, schema_version, payload_json, content_hash, received_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        ev.event_id,
                        ev.session_id,
                        ev.player_id,
                        ev.event_type,
                        ev.occurred_at.astimezone(timezone.utc).isoformat(),
                        ev.sequence,
                        ev.schema_version,
                        json.dumps(ev.payload, ensure_ascii=False, sort_keys=True),
                        chash,
                        now,
                    ),
                )
                results.append({"event_id": ev.event_id, "status": "accepted", "reason": None})
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT content_hash FROM events WHERE event_id = ?", (ev.event_id,)
                ).fetchone()
                if row and row["content_hash"] == chash:
                    results.append({"event_id": ev.event_id, "status": "duplicate", "reason": None})
                else:
                    results.append({
                        "event_id": ev.event_id,
                        "status": "rejected",
                        "reason": "event_id_conflict",
                    })
    return results
