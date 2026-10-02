"""FastAPI service. Run: uv run uvicorn app.api:app --port 8000"""

import json
import os
import time
from datetime import date

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.llm import LLM
from app.rag import Options, build_blocks, finalize, messages, retriever
from app.rag import answer as rag_answer
from app.schemas import QueryRequest, QueryResponse

STRATEGY = os.environ.get("INDEX_STRATEGY", "whole")
app = FastAPI(title="노동법령 RAG QA", version="0.1.0")
llm = LLM(budget_krw=float(os.environ.get("SERVER_BUDGET_KRW", "3000")))


@app.on_event("startup")
def warm() -> None:
    retriever(STRATEGY).search("워밍업", 1)  # load embedder + index before the first request


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "strategy": STRATEGY, "spent_krw": round(llm.spent_krw, 2)}


@app.post("/v1/query", response_model=QueryResponse)
def query(req: QueryRequest):
    opt = Options(strategy=STRATEGY, top_k=req.top_k, precedents=req.precedents)
    if not req.stream:
        return rag_answer(req.question, opt, req.as_of, llm)
    return StreamingResponse(_sse(req, opt), media_type="text/event-stream")


def _event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse(req: QueryRequest, opt: Options):
    """`delta` events carry answer text; one `final` event carries the full QueryResponse."""
    t0, as_of = time.time(), (req.as_of or date.today()).isoformat()
    blocks = build_blocks(req.question, opt, as_of)
    retrieval = [{"rank": i + 1, "chunk_id": b.chunk_id, "article_ids": b.article_ids, "score": round(b.score, 4),
                  "linked": b.linked, "via": b.via} for i, b in enumerate(blocks)]
    meta = {"prompt_version": opt.prompt, "strategy": opt.strategy, "as_of": as_of, "model": None,
            "usage": None, "cost_krw": 0.0}
    if not blocks or blocks[0].score < opt.tau:
        yield _event("final", {"status": "insufficient_context", "answer": None, "citations": [],
                               "retrieval": retrieval, "meta": {**meta, "refusal_reason": "retrieval_below_tau",
                                                                "latency_ms": int((time.time() - t0) * 1000)}})
        return
    before, parts = llm.spent_krw, []
    for delta in llm.stream(messages(req.question, blocks, as_of, opt.inject_status, opt.prompt), max_tokens=800):
        parts.append(delta)
        yield _event("delta", {"text": delta})
    text = "".join(parts)
    status, citations, reason = finalize(text, blocks)
    u = llm.last_stream_meta
    yield _event("final", {
        "status": status, "answer": text if status == "answered" else None, "citations": citations,
        "retrieval": retrieval,
        "meta": {**meta, "model": u.get("model"), "refusal_reason": reason,
                 "usage": {"input": u.get("prompt_tokens", 0), "output": u.get("completion_tokens", 0)},
                 "cost_krw": round(llm.spent_krw - before, 4), "latency_ms": int((time.time() - t0) * 1000)},
    })
