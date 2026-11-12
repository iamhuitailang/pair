"""analysis 测试：确定性、乱序、缺失、重复、时间倒退、完整率、胜负。"""
from datetime import datetime, timedelta, timezone

from app.analysis import RULES_VERSION, analyze

BASE = datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc)


def ev(event_id, seq, player="p1", etype="kill", minutes=0, payload=None):
    return {
        "event_id": event_id,
        "session_id": "s1",
        "player_id": player,
        "event_type": etype,
        "occurred_at": BASE + timedelta(minutes=minutes),
        "sequence": seq,
        "payload": payload or {},
    }


def test_deterministic_regardless_of_input_order():
    events = [ev("a", 0, minutes=0), ev("b", 1, minutes=1), ev("c", 2, minutes=2)]
    r1 = analyze(events)
    r2 = analyze(list(reversed(events)))
    assert r1 == r2
    assert r1["rules_version"] == RULES_VERSION


def test_out_of_order_arrival_produces_sorted_timeline():
    events = [ev("c", 2, minutes=2), ev("a", 0, minutes=0), ev("b", 1, minutes=1)]
    result = analyze(events)
    assert [e["event_id"] for e in result["timeline"]] == ["a", "b", "c"]
    assert result["anomalies"] == []


def test_missing_sequence_detected_and_completeness():
    events = [ev("a", 0), ev("c", 2), ev("d", 3)]  # 缺 seq 1
    result = analyze(events)
    missing = [a for a in result["anomalies"] if a["type"] == "missing_sequence"]
    assert missing and missing[0]["missing"] == [1]
    assert result["metrics"]["completeness"] == 0.75  # 3/4
    assert result["has_anomalies"]


def test_duplicate_sequence_flagged():
    events = [ev("a", 0), ev("b", 1, minutes=1), ev("b2", 1, etype="death", minutes=1)]
    result = analyze(events)
    dup = [a for a in result["anomalies"] if a["type"] == "duplicate_sequence"]
    assert dup and set(dup[0]["event_ids"]) == {"b", "b2"}


def test_time_regression_flagged():
    events = [ev("a", 0, minutes=5), ev("b", 1, minutes=2)]  # seq 1 时间早于 seq 0
    result = analyze(events)
    reg = [a for a in result["anomalies"] if a["type"] == "time_regression"]
    assert reg and reg[0]["event_id"] == "b"
    flags = {e["event_id"]: e["flags"] for e in result["timeline"]}
    assert "time_regression" in flags["b"]


def test_unknown_event_type_flagged():
    result = analyze([ev("a", 0, etype="teleport_hack")])
    assert any(a["type"] == "unknown_event_type" for a in result["anomalies"])


def test_duration_and_action_counts():
    events = [
        ev("a", 0, etype="game_start", minutes=0),
        ev("b", 1, etype="kill", minutes=3),
        ev("c", 2, etype="kill", minutes=5),
        ev("d", 3, etype="game_end", minutes=10, payload={"winner_player_id": "p1"}),
    ]
    m = analyze(events)["metrics"]
    assert m["duration_seconds"] == 600
    assert m["action_counts"]["kill"] == 2
    assert m["winner_player_id"] == "p1"
    assert analyze(events)["status"] == "finished"


def test_in_progress_without_game_end():
    assert analyze([ev("a", 0)])["status"] == "in_progress"


def test_client_reported_stats_ignored():
    # payload 里自称的统计一律不采用，胜负只看 game_end.winner_player_id
    events = [
        ev("a", 0, etype="game_end", payload={"winner_player_id": "p2", "kills": 999}),
        ev("b", 1, etype="kill", payload={"client_total_kills": 999}),
    ]
    m = analyze(events)["metrics"]
    assert m["winner_player_id"] == "p2"
    assert m["action_counts"]["kill"] == 1  # 来自事件本身，不是客户端的 999


def test_multi_player_sequences_independent():
    events = [
        ev("a", 0, player="p1"), ev("b", 1, player="p1", minutes=1),
        ev("c", 0, player="p2"),  # p2 自己的序号从 0 开始，不算缺失
    ]
    result = analyze(events)
    assert not [a for a in result["anomalies"] if a["type"] == "missing_sequence"]
    assert result["metrics"]["completeness"] == 1.0


def test_unknown_rules_version_rejected():
    import pytest

    with pytest.raises(ValueError):
        analyze([ev("a", 0)], rules_version="999")
