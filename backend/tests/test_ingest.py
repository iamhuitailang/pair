"""ingest 测试：去重、部分失败、未知版本、冲突、大小限制。"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = str(tmp_path / "test.db")
    monkeypatch.setenv("GAME_REPLAY_DB", db)
    # 每个测试用独立 DB，重新构建 app
    import importlib

    import app.main
    importlib.reload(app.main)
    return TestClient(app.main.app)


def make_event(event_id="e1", session_id="s1", player_id="p1", **kw):
    ev = {
        "event_id": event_id,
        "session_id": session_id,
        "player_id": player_id,
        "event_type": "kill",
        "occurred_at": "2026-11-12T10:00:00+00:00",
        "sequence": 0,
        "schema_version": 1,
        "payload": {},
    }
    ev.update(kw)
    return ev


def post(client, events):
    return client.post("/api/events/batch", json={"events": events})


def test_accept_single(client):
    r = post(client, [make_event()])
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] == 1
    assert body["results"][0]["status"] == "accepted"


def test_duplicate_not_counted_twice(client):
    ev = make_event()
    post(client, [ev])
    r = post(client, [ev]).json()
    assert r["duplicates"] == 1 and r["accepted"] == 0
    detail = client.get("/api/sessions/s1").json()
    assert detail["event_count"] == 1


def test_event_id_conflict_rejected(client):
    post(client, [make_event()])
    r = post(client, [make_event(payload={"x": 1})]).json()
    assert r["results"][0]["status"] == "rejected"
    assert r["results"][0]["reason"] == "event_id_conflict"


def test_bad_event_does_not_fail_batch(client):
    good = make_event("good")
    bad_missing_field = make_event("bad1")
    del bad_missing_field["player_id"]
    bad_version = make_event("bad2", schema_version=99)
    bad_seq = make_event("bad3", sequence=-1)
    bad_time = make_event("bad4", occurred_at="not-a-time")
    r = post(client, [good, bad_missing_field, bad_version, bad_seq, bad_time]).json()
    assert r["accepted"] == 1
    assert r["rejected"] == 4
    reasons = {x["event_id"]: x["reason"] for x in r["results"]}
    assert "unsupported_schema_version" in reasons["bad2"]
    assert reasons["bad1"].startswith("invalid_field:player_id")
    detail = client.get("/api/sessions/s1").json()
    assert detail["event_count"] == 1


def test_naive_datetime_rejected(client):
    r = post(client, [make_event(occurred_at="2026-11-12T10:00:00")]).json()
    assert r["results"][0]["status"] == "rejected"


def test_batch_size_limit(client):
    r = post(client, [make_event(f"e{i}", sequence=i) for i in range(501)])
    assert r.status_code == 422


def test_body_size_limit(client):
    big = make_event(payload={"blob": "x" * (1024 * 1024)})
    r = post(client, [big])
    assert r.status_code == 413
