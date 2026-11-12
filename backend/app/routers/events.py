"""事件写入接口。"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..ingest import ingest_batch
from ..schemas import MAX_BATCH_SIZE, BatchIn

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/batch")
def post_batch(body: BatchIn, request: Request):
    if len(body.events) > MAX_BATCH_SIZE:
        return JSONResponse(
            status_code=422,
            content={"detail": f"batch too large: {len(body.events)} > {MAX_BATCH_SIZE}"},
        )
    results = ingest_batch(body.events, db_path=request.app.state.db_path)
    accepted = sum(1 for r in results if r["status"] == "accepted")
    return {
        "total": len(results),
        "accepted": accepted,
        "duplicates": sum(1 for r in results if r["status"] == "duplicate"),
        "rejected": sum(1 for r in results if r["status"] == "rejected"),
        "results": results,
    }
