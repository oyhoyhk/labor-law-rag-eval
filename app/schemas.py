"""Request / response schema for POST /v1/query."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    as_of: date | None = Field(default=None, description="기준일. 생략 시 요청일")
    stream: bool = False


class Citation(BaseModel):
    source: str = Field(description="답변 본문의 [S#] 표기")
    chunk_id: str
    article_ids: list[str]
    law: str
    article: str
    quote: str = Field(description="근거 블록에서 답변과 가장 많이 겹치는 항")
    url: str
    status: Literal["in_force", "amendment_pending", "partially_expired", "expired", "pending", "unknown"]
    status_notes: list[str] = []


class RetrievalHit(BaseModel):
    chunk_id: str
    score: float
    linked: bool = Field(default=False, description="검색이 아니라 위임 관계로 확장된 블록")


class Usage(BaseModel):
    input: int
    output: int
    cached_input: int = 0


class Meta(BaseModel):
    model: str | None
    prompt_version: str
    strategy: str
    as_of: date
    latency_ms: int
    usage: Usage | None
    cost_krw: float
    refusal_reason: str | None = None


class QueryResponse(BaseModel):
    status: Literal["answered", "insufficient_context"]
    answer: str | None
    citations: list[Citation]
    retrieval: list[RetrievalHit]
    meta: Meta
