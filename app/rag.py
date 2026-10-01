"""Retrieve → link-expand → refusal gate → generate → validate citations.

Answers cite context blocks inline as [S1]; citations are derived from those
markers, so streaming and non-streaming share one output format.
"""

import json
import re
import time
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from urllib.parse import quote

from app.index import INDEX_DIR, Retriever
from app.ingest.provision import GRAPH, status_at
from app.llm import LLM

PROMPT_VERSION = "gen-v1"
TAU = 0.50  # top-1 cosine below this → refuse without calling the LLM (calibrated in H3)
MAX_LINKED = 3
REFUSAL = "[정보 부족]"
MARKER = re.compile(r"\[S(\d+)\]")

SYSTEM = """당신은 한국 노동법령 질의응답 도우미입니다. 아래 [근거] 블록만 사용해 답하세요.
규칙:
1. 근거 블록에 없는 내용은 쓰지 않는다. 일반 지식, 판례, 행정해석으로 보충하지 않는다.
2. 사실을 말하는 모든 문장 끝에 근거 블록 번호를 [S1]처럼 붙인다.
3. 근거 블록의 '시행 상태'에 효력 상실이나 시행 예정이 적혀 있으면, 답변에 그 사실과 날짜를 밝힌다. 기준일은 {as_of}이다.
4. 근거 블록으로 답할 수 없으면 첫 줄을 정확히 "[정보 부족]"으로 쓰고, 무엇이 없는지만 한 문장으로 쓴다.
5. 간결하게 답한다."""


@dataclass
class Options:
    strategy: str = "article"
    top_k: int = 5
    inject_status: bool = True  # H4 switch
    expand_links: bool = True
    tau: float = TAU


@dataclass
class Block:
    source: str
    chunk_id: str
    article_ids: list[str]
    text: str
    score: float
    linked: bool = False
    status: dict = field(default_factory=dict)


@lru_cache(maxsize=2)
def retriever(strategy: str) -> Retriever:
    return Retriever(strategy)


@lru_cache(maxsize=1)
def graph() -> dict:
    return json.loads(GRAPH.read_text())["nodes"]


@lru_cache(maxsize=1)
def article_texts() -> dict[str, str]:
    """article_id -> full article text, used for link expansion regardless of strategy."""
    out: dict[str, str] = {}
    for line in (INDEX_DIR / "article" / "chunks.jsonl").open():
        c = json.loads(line)
        aid = c["article_ids"][0]
        out[aid] = out[aid] + "\n" + c["text"].split("\n", 1)[1] if aid in out else c["text"]
    return out


def _status(article_ids: list[str], as_of: str) -> dict:
    """Worst status across the articles in a block, with all notes."""
    order = ["expired", "partially_expired", "unknown", "amendment_pending", "pending", "in_force"]
    sts = [status_at(graph()[a], as_of) for a in article_ids if a in graph()]
    if not sts:
        return {"status": "unknown", "notes": []}
    return {"status": min((s["status"] for s in sts), key=order.index), "notes": [n for s in sts for n in s["notes"]]}


def _render(b: Block, as_of: str, inject: bool) -> str:
    lines = [f"[{b.source}]" + (" (위임 관계로 연결된 조문)" if b.linked else "")]
    if inject:
        label = {"in_force": "시행 중", "amendment_pending": "시행 중(개정 예정 있음)", "partially_expired": "일부 효력 상실",
                 "expired": "효력 상실", "pending": "아직 시행 전", "unknown": "확인 필요"}[b.status["status"]]
        lines.append(f"시행 상태(기준일 {as_of}): {label}" + ("".join(f"\n- {n}" for n in b.status["notes"])))
        for aid in b.article_ids:
            for p in graph().get(aid, {}).get("pending", []):
                if p["effective"] > as_of and p["changed_paragraphs"]:
                    lines.append(f"[{p['effective']} 시행 예정 개정 내용] " + " / ".join(p["changed_paragraphs"]))
    lines.append(b.text)
    return "\n".join(lines)


def build_blocks(question: str, opt: Options, as_of: str) -> list[Block]:
    hits = retriever(opt.strategy).search(question, opt.top_k)
    blocks = [Block(f"S{i + 1}", h["chunk_id"], h["article_ids"], h["text"], h["score"]) for i, h in enumerate(hits)]
    if opt.expand_links:
        seen = {a for b in blocks for a in b.article_ids}
        for b in list(blocks[:3]):
            for aid in b.article_ids:
                node = graph().get(aid, {})
                for linked in node.get("delegates_to", []) + node.get("delegated_from", []):
                    if linked not in seen and linked in article_texts() and len(blocks) < opt.top_k + MAX_LINKED:
                        seen.add(linked)
                        blocks.append(Block(f"S{len(blocks) + 1}", f"art:{linked}", [linked],
                                            article_texts()[linked], 0.0, linked=True))
    for b in blocks:
        b.status = _status(b.article_ids, as_of)
    return blocks


def messages(question: str, blocks: list[Block], as_of: str, inject: bool) -> list[dict]:
    context = "\n\n".join(_render(b, as_of, inject) for b in blocks)
    return [{"role": "system", "content": SYSTEM.format(as_of=as_of)},
            {"role": "user", "content": f"[근거]\n{context}\n\n[질문]\n{question}"}]


def _bigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _quote(block: Block, sentences: list[str]) -> str:
    paras = [p for p in block.text.split("\n")[1:] if p.strip()] or [block.text]
    target = _bigrams(" ".join(sentences))
    return max(paras, key=lambda p: len(_bigrams(p) & target))[:300]


def _article_url(aid: str) -> str:
    law, key = aid.split("#")
    num, _, branch = key.partition("의")
    return f"https://www.law.go.kr/법령/{quote(law)}/제{num}조" + (f"의{branch}" if branch else "")


def _label(aid: str) -> str:
    law, key = aid.split("#")
    num, _, branch = key.partition("의")
    return f"제{num}조" + (f"의{branch}" if branch else "")


def finalize(answer: str, blocks: list[Block]) -> tuple[str, list[dict], str | None]:
    """Returns (status, citations, refusal_reason) from the raw model answer."""
    if answer.strip().startswith(REFUSAL):
        return "insufficient_context", [], "model_declined"
    by_source = {b.source: b for b in blocks}
    sentences: dict[str, list[str]] = {}
    for sent in re.split(r"(?<=[.다요])\s+|\n", answer):
        for n in MARKER.findall(sent):
            sentences.setdefault(f"S{n}", []).append(sent)
    citations = []
    for src, sents in sentences.items():
        b = by_source.get(src)
        if b is None:
            continue  # marker pointing at a block that does not exist
        primary = b.article_ids[0]
        citations.append({
            "source": src, "chunk_id": b.chunk_id, "article_ids": b.article_ids, "law": primary.split("#")[0],
            "article": " · ".join(_label(a) for a in b.article_ids), "quote": _quote(b, sents),
            "url": _article_url(primary), "status": b.status["status"], "status_notes": b.status["notes"],
        })
    if not citations:
        return "insufficient_context", [], "no_valid_citation"
    return "answered", citations, None


def answer(question: str, opt: Options | None = None, as_of: date | None = None, llm: LLM | None = None) -> dict:
    opt, t0 = opt or Options(), time.time()
    as_of_s = (as_of or date.today()).isoformat()
    llm = llm or LLM()
    blocks = build_blocks(question, opt, as_of_s)
    retrieval = [{"chunk_id": b.chunk_id, "score": round(b.score, 4), "linked": b.linked} for b in blocks]
    base_meta = {"prompt_version": PROMPT_VERSION, "strategy": opt.strategy, "as_of": as_of_s}

    if not blocks or blocks[0].score < opt.tau:
        return {"status": "insufficient_context", "answer": None, "citations": [], "retrieval": retrieval,
                "meta": {**base_meta, "model": None, "latency_ms": int((time.time() - t0) * 1000),
                         "usage": None, "cost_krw": 0.0, "refusal_reason": "retrieval_below_tau"}}

    before = llm.spent_krw
    text, usage = llm.chat(messages(question, blocks, as_of_s, opt.inject_status), max_tokens=800)
    status, citations, reason = finalize(text, blocks)
    return {"status": status, "answer": text if status == "answered" else None, "citations": citations,
            "retrieval": retrieval,
            "meta": {**base_meta, "model": usage["model"], "latency_ms": int((time.time() - t0) * 1000),
                     "usage": {"input": usage["prompt_tokens"], "output": usage["completion_tokens"],
                               "cached_input": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0},
                     "cost_krw": round(llm.spent_krw - before, 4), "refusal_reason": reason, "raw_answer": text}}
