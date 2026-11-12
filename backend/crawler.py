"""采集引擎：单工作线程顺序处理运行队列，遵守同域限制与请求间隔。"""
import threading
import time

import httpx
from bs4 import BeautifulSoup

import db
from urltools import content_hash, normalize_url, resolve, same_origin

USER_AGENT = "LocalCrawlTracker/1.0 (+https://localhost; respectful bot)"

_queue: list[int] = []
_cond = threading.Condition()
_worker_started = False


def enqueue_run(run_id: int):
    with _cond:
        _queue.append(run_id)
        _cond.notify()


def start_worker():
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    t = threading.Thread(target=_worker_loop, name="crawl-worker", daemon=True)
    t.start()


def _worker_loop():
    while True:
        with _cond:
            while not _queue:
                _cond.wait()
            run_id = _queue.pop(0)
        try:
            run_crawl(run_id)
        except Exception as exc:  # 兜底，保证线程不死
            db.update_run(run_id, status="failed", error=str(exc)[:500],
                          finished_at=time.time())


def run_crawl(run_id: int):
    run = db.get_run(run_id)
    if not run:
        return
    rule = db.get_rule(run["rule_id"])
    if not rule:
        db.update_run(run_id, status="failed", error="rule not found",
                      finished_at=time.time())
        return

    db.update_run(run_id, status="running", started_at=time.time())

    start_url = normalize_url(rule["start_url"])
    allowed_base = rule["allowed_domain"] or rule["start_url"]
    delay = max(0.0, float(rule["delay_seconds"]))
    timeout = max(1.0, float(rule["timeout_seconds"]))
    max_retries = max(0, int(rule["max_retries"]))
    max_pages = max(1, int(rule["max_pages"]))
    max_depth = max(0, int(rule["max_depth"]))
    link_scope = rule["link_scope"] or "all"

    prev_run = db.previous_finished_run(rule["id"], run_id)
    prev_map = db.pages_map_of_run(prev_run["id"]) if prev_run else {}

    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(start_url, 0)]
    counters = dict(new=0, modified=0, unchanged=0, error=0)
    last_request_at = 0.0

    client = httpx.Client(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=timeout,
    )
    try:
        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)
            if url in visited or depth > max_depth:
                continue
            visited.add(url)
            db.update_run(run_id, queued_count=len(queue), processing_count=1)

            # 请求间隔（限速）
            wait = delay - (time.monotonic() - last_request_at)
            if wait > 0:
                time.sleep(wait)
            http_status, html, err = _fetch(client, url, max_retries)
            last_request_at = time.monotonic()

            if err is not None:
                counters["error"] += 1
                db.insert_page({
                    "run_id": run_id, "rule_id": rule["id"], "url": url,
                    "title": "", "content": f"[fetch error] {err}",
                    "updated_at_text": "", "content_hash": "",
                    "status": "error", "http_status": http_status, "depth": depth,
                })
            else:
                title, content, updated_text, links = _extract(rule, url, html)
                h = content_hash(content)
                prev = prev_map.get(url)
                if prev is None:
                    status = "new"
                elif prev["content_hash"] != h:
                    status = "modified"
                else:
                    status = "unchanged"
                counters[status] += 1
                db.insert_page({
                    "run_id": run_id, "rule_id": rule["id"], "url": url,
                    "title": title, "content": content,
                    "updated_at_text": updated_text, "content_hash": h,
                    "status": status, "http_status": http_status, "depth": depth,
                })
                # 发现新链接（同域 + 去重 + 深度限制）
                for link in links:
                    if link not in visited and same_origin(link, allowed_base):
                        if not any(u == link for u, _ in queue):
                            queue.append((link, depth + 1))

            db.update_run(
                run_id,
                queued_count=len(queue),
                processing_count=0,
                done_count=len(visited),
                new_count=counters["new"],
                modified_count=counters["modified"],
                unchanged_count=counters["unchanged"],
                error_count=counters["error"],
            )
    finally:
        client.close()

    # 增量对比：上一轮有、本轮没抓到的页面 → disappeared
    disappeared = 0
    for url, prev in prev_map.items():
        if url not in visited and prev["status"] != "error":
            disappeared += 1
            db.insert_page({
                "run_id": run_id, "rule_id": rule["id"], "url": url,
                "title": prev["title"], "content": "",
                "updated_at_text": prev["updated_at_text"],
                "content_hash": "", "status": "disappeared",
                "http_status": None, "depth": prev["depth"],
            })
    db.update_run(run_id, disappeared_count=disappeared, queued_count=0,
                  processing_count=0, status="finished", finished_at=time.time())


def _fetch(client: httpx.Client, url: str, max_retries: int):
    """返回 (http_status, html, error)。对 5xx/429/网络错误做指数退避重试；
    其他 4xx 不重试，直接记为错误。"""
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.get(url)
            if resp.status_code < 400:
                return resp.status_code, resp.text, None
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                last_err = f"HTTP {resp.status_code}"
                time.sleep(min(0.5 * (2 ** attempt), 5.0))
                continue
            return resp.status_code, None, f"HTTP {resp.status_code}"
        except httpx.HTTPError as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < max_retries:
                time.sleep(min(0.5 * (2 ** attempt), 5.0))
    return None, None, last_err


def _extract(rule, page_url: str, html: str):
    """抽取标题/正文/更新时间，并收集链接。返回 (title, content, updated_text, links)。"""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if rule["title_selector"]:
        el = soup.select_one(rule["title_selector"])
        if el:
            title = el.get_text(strip=True)
    if not title and soup.title:
        title = soup.title.get_text(strip=True)

    content = ""
    if rule["content_selector"]:
        el = soup.select_one(rule["content_selector"])
        if el:
            content = el.get_text("\n", strip=True)
    if not content:
        body = soup.body or soup
        content = body.get_text("\n", strip=True)

    updated_text = ""
    if rule["time_selector"]:
        el = soup.select_one(rule["time_selector"])
        if el:
            updated_text = el.get_text(strip=True)
    if not updated_text:
        el = soup.select_one(".updated, time, [datetime]")
        if el:
            updated_text = el.get("datetime") or el.get_text(strip=True)

    links: list[str] = []
    if rule["link_scope"] == "next":
        anchors = []
        if rule["next_selector"]:
            anchors = soup.select(rule["next_selector"])
    else:
        anchors = soup.find_all("a")
        if rule["next_selector"]:
            anchors += soup.select(rule["next_selector"])
    for a in anchors:
        u = resolve(page_url, a.get("href"))
        if u:
            links.append(u)

    return title, content, updated_text, links
