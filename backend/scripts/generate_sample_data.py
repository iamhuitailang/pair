"""生成示例数据：覆盖正常对局、乱序、重试去重、坏事件、迟到事件。

用法：先启动服务（uvicorn app.main:app），再运行
    python scripts/generate_sample_data.py [base_url]
"""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def post(events):
    req = urllib.request.Request(
        f"{BASE}/api/events/batch",
        data=json.dumps({"events": events}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def ev(eid, sid, pid, etype, ts, seq, payload=None, ver=1):
    return {
        "event_id": eid,
        "session_id": sid,
        "player_id": pid,
        "event_type": etype,
        "occurred_at": ts,
        "sequence": seq,
        "schema_version": ver,
        "payload": payload or {},
    }


def show(title, resp):
    print(f"\n== {title} ==")
    print(f"  total={resp['total']} accepted={resp['accepted']} "
          f"duplicates={resp['duplicates']} rejected={resp['rejected']}")
    for r in resp["results"]:
        if r["status"] != "accepted":
            print(f"  {r['status']:9s} {r['event_id']}: {r['reason']}")


# ---------- 1. 正常对局 s-normal：两名玩家，完整打完 ----------
normal = [
    ev("n01", "s-normal", "p1", "session_start", "2026-11-12T10:00:00+00:00", 0),
    ev("n02", "s-normal", "p1", "game_start",    "2026-11-12T10:00:05+00:00", 1),
    ev("n03", "s-normal", "p1", "kill",          "2026-11-12T10:03:00+00:00", 2, {"target": "p2"}),
    ev("n04", "s-normal", "p1", "item_pickup",   "2026-11-12T10:05:00+00:00", 3, {"item": "sword"}),
    ev("n05", "s-normal", "p1", "game_end",      "2026-11-12T10:10:00+00:00", 4, {"winner_player_id": "p1"}),
    ev("n06", "s-normal", "p2", "session_start", "2026-11-12T10:00:01+00:00", 0),
    ev("n07", "s-normal", "p2", "game_start",    "2026-11-12T10:00:06+00:00", 1),
    ev("n08", "s-normal", "p2", "death",         "2026-11-12T10:03:01+00:00", 2, {"by": "p1"}),
    ev("n09", "s-normal", "p2", "game_end",      "2026-11-12T10:10:01+00:00", 3, {"winner_player_id": "p1"}),
]
show("1. 正常对局 s-normal", post(normal))

# ---------- 2. 乱序对局 s-ooo：同一批里事件乱序到达 + 缺失序号 + 时间倒退 ----------
ooo = [
    ev("o03", "s-ooo", "p1", "kill",        "2026-11-12T11:05:00+00:00", 3),
    ev("o01", "s-ooo", "p1", "game_start",  "2026-11-12T11:00:00+00:00", 0),
    ev("o04", "s-ooo", "p1", "item_pickup", "2026-11-12T11:02:00+00:00", 4),  # 时间倒退（seq 4 早于 seq 3）
    ev("o05", "s-ooo", "p1", "game_end",    "2026-11-12T11:20:00+00:00", 5, {"winner_player_id": "p2"}),
    # 缺 seq 1、2 -> missing_sequence
]
show("2. 乱序+缺失+时间倒退 s-ooo", post(ooo))

# ---------- 3. 重试去重：整批重发 s-normal ----------
show("3. 整批重试（应全部 duplicate）", post(normal))

# ---------- 4. 混合坏事件：好事件应正常接收 ----------
mixed = [
    ev("m01", "s-mixed", "p1", "game_start", "2026-11-12T12:00:00+00:00", 0),
    {  # 缺 player_id
        "event_id": "m02", "session_id": "s-mixed", "event_type": "kill",
        "occurred_at": "2026-11-12T12:01:00+00:00", "sequence": 1,
        "schema_version": 1, "payload": {},
    },
    ev("m03", "s-mixed", "p1", "kill", "2026-11-12T12:02:00+00:00", 2, ver=99),  # 未知 schema_version
    ev("m04", "s-mixed", "p1", "kill", "not-a-time", 3),                          # 非法时间
    ev("m05", "s-mixed", "p1", "kill", "2026-11-12T12:03:00+00:00", -1),          # 负序号
    ev("m06", "s-mixed", "p1", "teleport_hack", "2026-11-12T12:04:00+00:00", 4),  # 未知事件类型（接收但标记）
    ev("m07", "s-mixed", "p1", "game_end", "2026-11-12T12:10:00+00:00", 5, {"winner_player_id": "p1"}),
]
show("4. 混合坏事件 s-mixed（好事件应接收）", post(mixed))

# ---------- 5. 迟到事件：s-normal 的 game_end 之后补发一条更早发生的事件 ----------
late = [
    ev("n10", "s-normal", "p2", "item_pickup", "2026-11-12T10:04:00+00:00", 4, {"item": "shield"}),
]
show("5. 迟到事件（接收并重算 s-normal）", post(late))

print("\n完成。打开 http://localhost:8010 查看：")
print("  - s-normal：迟到事件已并入时间线，完整率 100%；")
print("    因迟到事件 seq 4 的 occurred_at 早于 seq 3，被规则标记为时间倒退（演示重算效果）")
print("  - s-ooo：缺失序号 [1,2]、时间倒退、乱序后时间线仍按时间排序")
print("  - s-mixed：4 条拒收、teleport_hack 标记未知类型、好事件正常统计")
