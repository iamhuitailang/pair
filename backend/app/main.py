"""FastAPI 入口：路由、请求体大小限制、前端静态文件托管。"""
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import events, sessions
from .schemas import MAX_BODY_BYTES

app = FastAPI(title="Game Replay Analytics")
app.state.db_path = os.environ.get("GAME_REPLAY_DB")
init_db(app.state.db_path)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "request body too large"})
    return await call_next(request)


app.include_router(events.router)
app.include_router(sessions.router)

# 前端构建产物（frontend/dist）由 FastAPI 托管，单进程即可访问
_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
