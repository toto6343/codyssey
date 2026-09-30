from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field


# ---------- data ----------
class DataCreate(BaseModel):
    date: Date = Field(description="주말 시작일(금요일), YYYY-MM-DD")
    value: int = Field(ge=0, le=1_000_000_000, description="상위 10편 관객수 합계")
    memo: str = Field(default="", max_length=200)


class DataUpdate(BaseModel):
    # date는 문서 ID로 쓰이므로 수정 대상에서 제외
    value: int = Field(ge=0, le=1_000_000_000)
    memo: str = Field(default="", max_length=200)


class DataOut(BaseModel):
    id: str
    date: str
    value: int
    memo: str = ""


class WeekendPoint(BaseModel):
    date: str
    value: int
    memo: str = ""


class Metrics(BaseModel):
    total: int
    average: int
    max: int
    max_date: str
    max_memo: str
    min: int
    min_date: str
    min_memo: str


class SummaryOut(BaseModel):
    period: str
    count: int
    metrics: Metrics
    latest: WeekendPoint
    trend: str
    trend_pct: float | None
    yoy: str | None
    yoy_pct: float | None
    top5: list[WeekendPoint]


class SyncOut(BaseModel):
    fetched: int  # KOBIS에서 정상 조회된 주말 수
    added: int  # 새로 저장된 수
    skipped: int  # 이미 있어서 건너뛴 수 (수정한 메모 보호)
    failed: int  # 조회 실패한 주 수


# ---------- conversations ----------
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    messages: list[Message] = Field(min_length=1, max_length=100)


class ConversationListItem(BaseModel):
    """목록 응답에는 messages를 포함하지 않는다. (전체 메시지는 GET /api/conversations/{id})"""

    id: str
    title: str
    message_count: int
    created_at: str | None
    updated_at: str | None


class ConversationOut(BaseModel):
    id: str
    title: str
    messages: list[Message]
    created_at: str | None
    updated_at: str | None


# ---------- chat ----------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, description="이어서 대화할 때만 전달")


class ToolCallOut(BaseModel):
    tool: str
    reason: str = ""
    args: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    tool_calls: list[ToolCallOut] = Field(default_factory=list)