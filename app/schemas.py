"""Request / response schema for POST /v1/query."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    as_of: date | None = Field(default=None, description="기준일. 생략 시 요청일")
    stream: bool = False
    precedents: bool = Field(default=False, description="검색된 조문에 연결된 대법원 판례를 근거로 함께 사용")


class Citation(BaseModel):
    source: str = Field(description="답변 본문의 [S#] 표기")
    source_type: Literal["statute", "precedent"] = Field(default="statute", description="조문 또는 대법원 판례")
    chunk_id: str
    article_ids: list[str] = Field(description="조문 ID(법령명#조) 또는 판례 ID(판례#사건번호)")
    law: str = Field(description="법령명, 판례는 '대법원'")
    article: str = Field(description="조문 표기, 판례는 '대법원 2024. 12. 19. 선고 2020다247190 판결'")
    quote: str = Field(description="근거 블록에서 답변과 가장 많이 겹치는 항")
    url: str
    status: Literal["in_force", "amendment_pending", "partially_expired", "expired", "pending", "unknown",
                    "not_applicable"] = Field(description="조문의 시행 상태, 판례는 not_applicable")
    status_notes: list[str] = []


class RetrievalHit(BaseModel):
    rank: int = Field(description="1부터 시작하는 순위. 확장 블록은 검색 순위 뒤에 이어짐")
    chunk_id: str
    article_ids: list[str] = Field(description="청크가 포함하는 조문 ID — GT gold_evidence와 같은 형식(법령명#조)")
    score: float
    linked: bool = Field(default=False, description="검색이 아니라 위임 관계로 확장된 블록")
    via: Literal["search", "sibling", "link", "reverse", "precedent"] = "search"


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
