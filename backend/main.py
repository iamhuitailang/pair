"""FastAPI 入口：规则管理、运行管理、结果查询、diff、导出。"""
import csv
import difflib
import io
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

import crawler
import db

app = FastAPI(title="Local Crawl Tracker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.init_db()
    crawler.start_worker()


# ---------- schemas ----------

class RuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_url: str = Field(min_length=1)
    allowed_domain: str = ""
    title_selector: str = ""
    content_selector: str = ""
    time_selector: str = ""
    next_selector: str = ""
    link_scope: str = "all"  # all | next
    max_pages: int = Field(default=200, ge=1, le=10000)
    max_depth: int = Field(default=5, ge=0, le=20)
    delay_seconds: float = Field(default=0.5, ge=0, le=60)
    timeout_seconds: float = Field(default=10, ge=1, le=120)
    max_retries: int = Field(default=2, ge=0, le=10)
    enabled: bool = True


class RulePatch(BaseModel):
    name: str | None = None
    start_url: str | None = None
    allowed_domain: str | None = None
    title_selector: str | None = None
    content_selector: str | None = None
    time_selector: str | None = None
    next_selector: str | None = None
    link_scope: str | None = None
    max_pages: int | None = Field(default=None, ge=1, le=10000)
    max_depth: int | None = Field(default=None, ge=0, le=20)
    delay_seconds: float | None = Field(default=None, ge=0, le=60)
    timeout_seconds: float | None = Field(default=None, ge=1, le=120)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    enabled: bool | None = None


# ---------- rules ----------

@app.get("/api/rules")
def list_rules():
    return db.list_rules()


@app.post("/api/rules", status_code=201)
def create_rule(body: RuleIn):
    data = body.model_dump()
    data["enabled"] = int(data["enabled"])
    if data["link_scope"] not in ("all", "next"):
        raise HTTPException(422, "link_scope must be 'all' or 'next'")
    return db.create_rule(data)


@app.get("/api/rules/{rule_id}")
def get_rule(rule_id: int):
    rule = db.get_rule(rule_id)
    if not rule:
        raise HTTPException(404, "rule not found")
    return rule


@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, body: RulePatch):
    if not db.get_rule(rule_id):
        raise HTTPException(404, "rule not found")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "enabled" in data:
        data["enabled"] = int(data["enabled"])
    if data.get("link_scope") and data["link_scope"] not in ("all", "next"):
        raise HTTPException(422, "link_scope must be 'all' or 'next'")
    return db.update_rule(rule_id, data)


@app.delete("/api/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int):
    if not db.get_rule(rule_id):
        raise HTTPException(404, "rule not found")
    db.delete_rule(rule_id)


# ---------- runs ----------

@app.post("/api/rules/{rule_id}/run", status_code=201)
def start_run(rule_id: int):
    rule = db.get_rule(rule_id)
    if not rule:
        raise HTTPException(404, "rule not found")
    run = db.create_run(rule_id)
    crawler.enqueue_run(run["id"])
    return run


@app.get("/api/runs")
def list_runs(rule_id: int | None = None):
    return db.list_runs(rule_id)


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@app.get("/api/runs/{run_id}/pages")
def run_pages(run_id: int, status: str | None = None):
    if not db.get_run(run_id):
        raise HTTPException(404, "run not found")
    return db.pages_of_run(run_id, status)


# ---------- diff ----------

def _diff_lines(old: str, new: str, fromfile: str, tofile: str):
    return list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=fromfile, tofile=tofile, lineterm="",
    ))


@app.get("/api/runs/{run_id}/diff")
def run_diff(run_id: int, compare_to: int | None = None):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    prev = db.get_run(compare_to) if compare_to else db.previous_finished_run(
        run["rule_id"], run_id)
    if not prev:
        return {"run_id": run_id, "compare_to": None, "items": []}
    prev_map = db.pages_map_of_run(prev["id"])
    items = []
    for page in db.pages_of_run(run_id):
        old = prev_map.get(page["url"])
        old_content = old["content"] if old else ""
        items.append({
            "url": page["url"],
            "status": page["status"],
            "title": page["title"],
            "old_updated_at": old["updated_at_text"] if old else "",
            "new_updated_at": page["updated_at_text"],
            "diff": _diff_lines(old_content, page["content"],
                                f"run#{prev['id']}", f"run#{run_id}"),
        })
    return {"run_id": run_id, "compare_to": prev["id"], "items": items}


@app.get("/api/pages/{page_id}/diff")
def page_diff(page_id: int, compare_to: int | None = None):
    page = db.get_page(page_id)
    if not page:
        raise HTTPException(404, "page not found")
    run = db.get_run(page["run_id"])
    prev_run = db.get_run(compare_to) if compare_to else db.previous_finished_run(
        run["rule_id"], run["id"])
    old = db.find_page_in_run(prev_run["id"], page["url"]) if prev_run else None
    old_content = old["content"] if old else ""
    return {
        "url": page["url"],
        "run_id": run["id"],
        "compare_to": prev_run["id"] if prev_run else None,
        "status": page["status"],
        "diff": _diff_lines(old_content, page["content"],
                            f"run#{prev_run['id']}" if prev_run else "∅",
                            f"run#{run['id']}"),
    }


# ---------- export ----------

@app.get("/api/runs/{run_id}/export")
def export_run(run_id: int, format: str = "json"):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    pages = db.pages_of_run(run_id)
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["url", "title", "status", "updated_at_text",
                         "http_status", "depth", "content"])
        for p in pages:
            writer.writerow([p["url"], p["title"], p["status"], p["updated_at_text"],
                             p["http_status"], p["depth"], p["content"]])
        return Response(
            content="﻿" + buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="run_{run_id}.csv"'},
        )
    payload = {
        "run": run,
        "pages": [{k: p[k] for k in ("url", "title", "status", "updated_at_text",
                                     "http_status", "depth", "content_hash", "content")}
                  for p in pages],
    }
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="run_{run_id}.json"'},
    )
