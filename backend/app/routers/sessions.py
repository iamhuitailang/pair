"""对局查询 / 时间线 / 导出接口。"""
import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from ..analysis import KNOWN_EVENT_TYPES, RULES_VERSION, get_analysis
from ..db import get_conn
from ..schemas import SUPPORTED_SCHEMA_VERSIONS

router = APIRouter(prefix="/api", tags=["sessions"])


def _list_sessions(conn, date_from, date_to, player_id):
    """按筛选条件取出 session_id 列表（按对局开始时间倒序）。"""
    sql = """
        SELECT session_id, MIN(occurred_at) AS started_at
        FROM events
        WHERE (? IS NULL OR occurred_at >= ?)
          AND (? IS NULL OR occurred_at <= ?)
          AND (? IS NULL OR player_id = ?)
        GROUP BY session_id
        ORDER BY started_at DESC
    """
    rows = conn.execute(sql, (date_from, date_from, date_to, date_to, player_id, player_id)).fetchall()
    return [r["session_id"] for r in rows]


def _summaries(conn, session_ids, status_filter):
    out = []
    for sid in session_ids:
        a = get_analysis(conn, sid)
        if status_filter and a["status"] != status_filter:
            continue
        m = a["metrics"]
        players = sorted({e["player_id"] for e in a["timeline"]})
        out.append({
            "session_id": sid,
            "status": a["status"],
            "has_anomalies": a["has_anomalies"],
            "anomaly_count": len(a["anomalies"]),
            "event_count": a["event_count"],
            "players": players,
            "started_at": m["started_at"],
            "duration_seconds": m["duration_seconds"],
            "winner_player_id": m["winner_player_id"],
            "completeness": m["completeness"],
        })
    return out


@router.get("/sessions")
def list_sessions(
    request: Request,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    player_id: str | None = Query(None),
    status: str | None = Query(None, pattern="^(finished|in_progress)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    with get_conn(request.app.state.db_path) as conn:
        sids = _list_sessions(conn, date_from, date_to, player_id)
        summaries = _summaries(conn, sids, status)
    total = len(summaries)
    start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size,
            "items": summaries[start:start + page_size]}


@router.get("/sessions/export")
def export_sessions(
    request: Request,
    format: str = Query("csv", pattern="^(csv|json)$"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    player_id: str | None = Query(None),
    status: str | None = Query(None, pattern="^(finished|in_progress)$"),
):
    with get_conn(request.app.state.db_path) as conn:
        sids = _list_sessions(conn, date_from, date_to, player_id)
        summaries = _summaries(conn, sids, status)

    if format == "json":
        return Response(
            content=json.dumps(summaries, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=sessions.json"},
        )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "session_id", "status", "has_anomalies", "anomaly_count", "event_count",
        "players", "started_at", "duration_seconds", "winner_player_id", "completeness",
    ])
    writer.writeheader()
    for s in summaries:
        row = dict(s)
        row["players"] = ";".join(s["players"])
        writer.writerow(row)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sessions.csv"},
    )


@router.get("/sessions/{session_id}")
def session_detail(
    request: Request,
    session_id: str,
    rules_version: str = Query(RULES_VERSION),
):
    with get_conn(request.app.state.db_path) as conn:
        exists = conn.execute(
            "SELECT 1 FROM events WHERE session_id=? LIMIT 1", (session_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="session not found")
        try:
            return get_analysis(conn, session_id, rules_version)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/meta")
def meta():
    return {
        "supported_schema_versions": sorted(SUPPORTED_SCHEMA_VERSIONS),
        "rules_version": RULES_VERSION,
        "known_event_types": sorted(KNOWN_EVENT_TYPES),
    }
