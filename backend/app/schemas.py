"""事件与批量请求的 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

SUPPORTED_SCHEMA_VERSIONS = {1}
MAX_BATCH_SIZE = 500
MAX_BODY_BYTES = 1 * 1024 * 1024  # 1MB


class EventIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    player_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=64)
    occurred_at: datetime  # 必须带时区
    sequence: int = Field(ge=0)
    schema_version: int
    payload: dict

    @field_validator("occurred_at")
    @classmethod
    def must_be_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("occurred_at 必须包含时区信息")
        return v


class BatchIn(BaseModel):
    events: list[dict]  # 逐条手动校验，保证一条坏事件不拖垮整批
