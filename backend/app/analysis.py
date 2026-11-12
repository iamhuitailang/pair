"""时间线重建与指标计算。纯函数：相同 (events, rules_version) 必得相同结果。"""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

RULES_VERSION = "1.0"

KNOWN_EVENT_TYPES = {
    "session_start",
    "player_join",
    "player_leave",
    "game_start",
    "kill",
    "death",
    "item_pickup",
    "objective",
    "game_end",
}


def _sort_key(ev: dict):
    return (ev["sequence"], ev["occurred_at"], ev["event_id"])


def analyze(events: list[dict], rules_version: str = RULES_VERSION) -> dict:
    """events: 每条形如 {event_id, session_id, player_id, event_type,
    occurred_at(datetime, UTC), sequence, payload(dict)}。
    """
    if rules_version != RULES_VERSION:
        raise ValueError(f"unknown rules_version: {rules_version}")

    anomalies: list[dict] = []
    event_flags: dict[str, list[str]] = defaultdict(list)

    # --- 按玩家分组做序号/时间检查（sequence 由每个玩家客户端独立维护）---
    by_player: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        by_player[ev["player_id"]].append(ev)

    total_expected = 0
    total_received = 0
    for player_id, evs in sorted(by_player.items()):
        evs_sorted = sorted(evs, key=_sort_key)

        # 未知事件类型
        for ev in evs_sorted:
            if ev["event_type"] not in KNOWN_EVENT_TYPES:
                event_flags[ev["event_id"]].append("unknown_event_type")
                anomalies.append({
                    "type": "unknown_event_type",
                    "player_id": player_id,
                    "event_id": ev["event_id"],
                    "detail": f"未知事件类型: {ev['event_type']}",
                })

        # 重复序号（同一玩家同一 sequence 出现多个不同 event_id）
        seq_seen: dict[int, list[dict]] = defaultdict(list)
        for ev in evs_sorted:
            seq_seen[ev["sequence"]].append(ev)
        for seq, group in sorted(seq_seen.items()):
            if len(group) > 1:
                for ev in group:
                    event_flags[ev["event_id"]].append("duplicate_sequence")
                anomalies.append({
                    "type": "duplicate_sequence",
                    "player_id": player_id,
                    "sequence": seq,
                    "event_ids": [e["event_id"] for e in group],
                    "detail": f"玩家 {player_id} 的序号 {seq} 出现 {len(group)} 个不同事件",
                })

        # 缺失序号
        distinct_seqs = set(seq_seen.keys())
        max_seq = max(distinct_seqs)
        expected = max_seq + 1
        missing = sorted(set(range(expected)) - distinct_seqs)
        total_expected += expected
        total_received += len(distinct_seqs)
        if missing:
            anomalies.append({
                "type": "missing_sequence",
                "player_id": player_id,
                "missing": missing,
                "detail": f"玩家 {player_id} 缺失序号: {missing}",
            })

        # 时间倒退：按 sequence 排序后 occurred_at 早于前一事件
        prev = None
        for ev in evs_sorted:
            if prev is not None and ev["occurred_at"] < prev["occurred_at"]:
                event_flags[ev["event_id"]].append("time_regression")
                anomalies.append({
                    "type": "time_regression",
                    "player_id": player_id,
                    "event_id": ev["event_id"],
                    "sequence": ev["sequence"],
                    "detail": (
                        f"序号 {ev['sequence']} 的时间 {ev['occurred_at'].isoformat()} "
                        f"早于序号 {prev['sequence']} 的时间 {prev['occurred_at'].isoformat()}"
                    ),
                })
            prev = ev

    # --- 指标 ---
    action_counts = Counter(ev["event_type"] for ev in events)

    game_ends = sorted(
        (ev for ev in events if ev["event_type"] == "game_end"),
        key=lambda e: (e["occurred_at"], e["event_id"]),
    )
    status = "finished" if game_ends else "in_progress"
    winner_player_id = None
    if game_ends:
        # 只从 game_end 的 payload 推导胜负；客户端上报的任何统计字段一律忽略
        winner = game_ends[0]["payload"].get("winner_player_id")
        winner_player_id = winner if isinstance(winner, str) else None

    times = [ev["occurred_at"] for ev in events]
    started_at = min(times) if times else None
    ended_at = max(times) if times else None
    duration_seconds = (ended_at - started_at).total_seconds() if times else 0.0

    completeness = (total_received / total_expected) if total_expected else 0.0

    # --- 时间线：按 (occurred_at, event_id) 确定性排序 ---
    timeline = [
        {
            "event_id": ev["event_id"],
            "player_id": ev["player_id"],
            "event_type": ev["event_type"],
            "occurred_at": ev["occurred_at"].isoformat(),
            "sequence": ev["sequence"],
            "payload": ev["payload"],
            "flags": sorted(event_flags.get(ev["event_id"], [])),
        }
        for ev in sorted(events, key=lambda e: (e["occurred_at"], e["event_id"]))
    ]

    return {
        "rules_version": rules_version,
        "event_count": len(events),
        "status": status,
        "has_anomalies": bool(anomalies),
        "metrics": {
            "duration_seconds": duration_seconds,
            "action_counts": dict(sorted(action_counts.items())),
            "winner_player_id": winner_player_id,
            "completeness": round(completeness, 4),
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": ended_at.isoformat() if ended_at else None,
        },
        "anomalies": anomalies,
        "timeline": timeline,
    }


# ---------- DB 层：加载事件 + 带缓存的分析 ----------

def load_events(conn, session_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM events WHERE session_id = ?", (session_id,)
    ).fetchall()
    return [
        {
            "event_id": r["event_id"],
            "session_id": r["session_id"],
            "player_id": r["player_id"],
            "event_type": r["event_type"],
            "occurred_at": datetime.fromisoformat(r["occurred_at"]).astimezone(timezone.utc),
            "sequence": r["sequence"],
            "payload": json.loads(r["payload_json"]),
        }
        for r in rows
    ]


def get_analysis(conn, session_id: str, rules_version: str = RULES_VERSION) -> dict:
    """读时计算 + 缓存：event_count 变化即失效重算。旧 rules_version 的结果保留可查询。"""
    events = load_events(conn, session_id)
    cached = conn.execute(
        "SELECT event_count, result_json FROM analysis_cache WHERE session_id=? AND rules_version=?",
        (session_id, rules_version),
    ).fetchone()
    if cached and cached["event_count"] == len(events):
        return json.loads(cached["result_json"])

    result = analyze(events, rules_version)
    conn.execute(
        """INSERT INTO analysis_cache (session_id, rules_version, event_count, result_json, computed_at)
           VALUES (?,?,?,?,?)
           ON CONFLICT(session_id, rules_version) DO UPDATE SET
             event_count=excluded.event_count, result_json=excluded.result_json,
             computed_at=excluded.computed_at""",
        (
            session_id,
            rules_version,
            len(events),
            json.dumps(result, ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return result
