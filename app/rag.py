"""Retrieve → link-expand → (precedent-expand) → refusal gate → generate → validate citations.

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

from app.index import INDEX_DIR, PrecedentScorer, Retriever
from app.ingest.precedent import load_precedents
from app.ingest.provision import GRAPH, status_at
from app.llm import LLM, cost_of

PROMPT_VERSION = "gen-v1"  # default generation prompt
PROMPT_VERSION_PARTIAL = "gen-v2-partial"  # adds a partial-answer mode between full answer and refusal
PROMPT_VERSION_PRECEDENT = "gen-v3-precedent"  # statute first, then linked Supreme Court holdings; set by --precedents
TAU = 0.50  # top-1 cosine below this → refuse without calling the LLM (calibrated in H3)
MAX_LINKED = 3
MAX_SIBLINGS = 4  # sibling-chunk cap → at most top_k + MAX_SIBLINGS + MAX_LINKED blocks
# Reverse-reference expansion: articles that reference a top-3 hit with an exception/준용 cue
# ("…제55조와 제60조를 적용하지 아니한다"). Ranked by how many top hits they reference, then cue
# (exception before 준용), then the best rank of the hit they reference; plain references are never added.
MAX_REVERSE = 2
REVERSE_CUES = ("exception", "mutatis")
# Precedent expansion: Supreme Court cases linked (참조조문) to a search hit's article, ranked by cosine(query,
# precedent); PREC_TAU chosen on the dev split only (README "판례 연결").
PREC_TAU = 0.54
MAX_PRECEDENTS = 2
PREC_HOLDING_CHARS = 3000  # ≈ p90 of 판결요지 length; longer ones cut at a sentence end, 판시사항 always whole
REFUSAL = "[정보 부족]"
MARKER = re.compile(r"\[S(\d+)\]")

SYSTEM = """당신은 한국 노동법령 질의응답 도우미입니다. 아래 [근거] 블록만 사용해 답하세요.
규칙:
1. 근거 블록에 없는 내용은 쓰지 않는다. 일반 지식, 판례, 행정해석으로 보충하지 않는다.
2. 사실을 말하는 모든 문장 끝에 근거 블록 번호를 [S1]처럼 붙인다.
3. 근거 블록의 '시행 상태'에 효력 상실이나 시행 예정이 적혀 있으면, 답변에 그 사실과 날짜를 밝힌다. 기준일은 {as_of}이다.
4. 근거 블록으로 답할 수 없으면 첫 줄을 정확히 "[정보 부족]"으로 쓰고, 무엇이 없는지만 한 문장으로 쓴다.
5. 간결하게 답한다."""

SYSTEM_PARTIAL = """당신은 한국 노동법령 질의응답 도우미입니다. 아래 [근거] 블록만 사용해 답하세요.
규칙:
1. 근거 블록에 없는 내용은 쓰지 않는다. 일반 지식, 판례, 행정해석으로 보충하지 않는다.
2. 사실을 말하는 모든 문장 끝에 근거 블록 번호를 [S1]처럼 붙인다.
3. 근거 블록의 '시행 상태'에 효력 상실이나 시행 예정이 적혀 있으면, 답변에 그 사실과 날짜를 밝힌다. 기준일은 {as_of}이다.
4. 근거 블록 문언에 질문의 사실을 대입해 반드시 따라 나오는 결론은 근거 블록으로 답할 수 있는 내용이다. 이 결론은 유보하지 말고 인용과 함께 쓴다.
5. 근거 블록이 질문의 일부에만 답하면, 답할 수 있는 부분을 먼저 인용과 함께 쓰고, 판단할 수 없는 부분은 "근거 블록만으로는 ~을 판단할 수 없다"고 한 문장으로 밝힌다. 판단할 수 없는 부분의 결론은 추측하지 않는다.
6. 질문이 묻는 쟁점에 답하는 내용이 근거 블록에 하나도 없으면, 주변 조문으로 답을 채우지 말고 첫 줄을 정확히 "[정보 부족]"으로 쓰고, 무엇이 없는지만 한 문장으로 쓴다. 근거 블록으로 답할 수 있는 내용이 있으면 "[정보 부족]"을 쓰지 않는다.
7. 질문에 답하는 데 쓰지 않는 조문은 소개하지 않는다. 간결하게 답한다."""

SYSTEM_PRECEDENT = """당신은 한국 노동법령 질의응답 도우미입니다. 아래 [근거] 블록만 사용해 답하세요. [근거] 블록은 법령 조문과, 검색된 조문에 연결된 대법원 판례("[판례]"로 시작하는 블록)로 이루어집니다.
규칙:
1. 근거 블록에 없는 내용은 쓰지 않는다. 일반 지식, 근거 블록에 없는 판례, 행정해석으로 보충하지 않는다.
2. 사실을 말하는 모든 문장 끝에 근거 블록 번호를 [S1]처럼 붙인다.
3. 근거 블록의 '시행 상태'에 효력 상실이나 시행 예정이 적혀 있으면, 답변에 그 사실과 날짜를 밝힌다. 기준일은 {as_of}이다.
4. 조문이 정한 내용을 먼저 쓴다.
5. 판례 블록이 질문의 쟁점에 관련되면, 조문 다음에 "대법원은 ~ 사안에서 ~라고 판단했습니다(대법원 2024. 12. 19. 선고 2020다247190 판결) [S3]"처럼 판례 블록의 판단을 사건번호·선고일과 함께 대법원의 판단으로 쓴다. 판례를 인용했으면 끝에 "다만 판례는 개별 사안의 사실관계에 따라 달리 판단될 수 있습니다."라고 덧붙인다.
6. 판례 블록을 인용하는 문장은 대법원의 판단임을 밝혀 쓴다. 판례의 판단을 "~법에 따라", "조문상"처럼 조문의 내용으로 쓰지 않는다. 질문과 관련 없는 판례 블록은 쓰지 않는다.
7. 조문 블록과 판례 블록으로 모두 답할 수 없으면 첫 줄을 정확히 "[정보 부족]"으로 쓰고, 무엇이 없는지만 한 문장으로 쓴다.
8. 한국어 합니다체로 간결하게 답한다."""

SYSTEMS = {PROMPT_VERSION: SYSTEM, PROMPT_VERSION_PARTIAL: SYSTEM_PARTIAL, PROMPT_VERSION_PRECEDENT: SYSTEM_PRECEDENT}


@dataclass
class Options:
    strategy: str = "article"
    top_k: int = 5
    inject_status: bool = True  # H4 switch
    expand_links: bool = True
    tau: float = TAU
    include_siblings: bool = False  # add the other chunks of a split article when one is retrieved
    expand_reverse_refs: bool = False
    prompt: str = PROMPT_VERSION  # key of SYSTEMS
    precedents: bool = False  # add linked Supreme Court precedents; switches the prompt to gen-v3-precedent

    def __post_init__(self):
        if self.precedents:
            self.prompt = PROMPT_VERSION_PRECEDENT


@dataclass
class Block:
    source: str
    chunk_id: str
    article_ids: list[str]
    text: str
    score: float
    linked: bool = False  # not a search hit (excluded from M1)
    via: str = "search"  # search | sibling | link | reverse | precedent
    status: dict = field(default_factory=dict)
    # reverse-ref blocks: the hits this article refers to; precedent blocks: the hit articles linking to the case
    referenced: list[str] = field(default_factory=list)


@lru_cache(maxsize=2)
def retriever(strategy: str) -> Retriever:
    return Retriever(strategy)


@lru_cache(maxsize=1)
def graph() -> dict:
    return json.loads(GRAPH.read_text())["nodes"]


@lru_cache(maxsize=1)
def precedents() -> dict:
    return load_precedents()


@lru_cache(maxsize=1)
def precedent_scorer() -> PrecedentScorer:
    return PrecedentScorer()


@lru_cache(maxsize=1)
def article_texts() -> dict[str, str]:
    """article_id -> full article text, used for link expansion regardless of strategy."""
    out: dict[str, str] = {}
    for line in (INDEX_DIR / "article" / "chunks.jsonl").open():
        c = json.loads(line)
        aid = c["article_ids"][0]
        out[aid] = out[aid] + "\n" + c["text"].split("\n", 1)[1] if aid in out else c["text"]
    return out


@lru_cache(maxsize=2)
def siblings(strategy: str) -> dict[str, list[dict]]:
    """chunk_id -> the other chunks of the same split article, in part order (article strategy only)."""
    parts: dict[str, list[dict]] = {}
    for c in retriever(strategy).chunks:
        if c.get("meta", {}).get("parts", 1) > 1:
            parts.setdefault(c["article_ids"][0], []).append(c)
    return {c["chunk_id"]: [o for o in group if o is not c] for group in parts.values() for c in group}


def _status(article_ids: list[str], as_of: str) -> dict:
    """Worst status across the articles in a block, with all notes."""
    order = ["expired", "partially_expired", "unknown", "amendment_pending", "pending", "in_force"]
    sts = [status_at(graph()[a], as_of) for a in article_ids if a in graph()]
    if not sts:
        return {"status": "unknown", "notes": []}
    return {"status": min((s["status"] for s in sts), key=order.index), "notes": [n for s in sts for n in s["notes"]]}


def _render(b: Block, as_of: str, inject: bool) -> str:
    if b.via == "precedent":
        return f"[{b.source}] (검색된 조문 {'·'.join(_title(a) for a in b.referenced)}에 연결된 대법원 판례)\n{b.text}"
    if b.referenced:
        note = f" ({'·'.join(_label(a) for a in b.referenced)}의 예외·준용을 정한 조문)"
    else:
        note = {"link": " (위임 관계로 연결된 조문)", "sibling": " (검색된 조문의 나머지 부분)"}.get(b.via, "")
    lines = [f"[{b.source}]" + note]
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
    n_sib = 0
    if opt.include_siblings:
        have = {b.chunk_id for b in blocks}
        for h in hits:  # in retrieval order, so higher-ranked articles get siblings first
            for c in siblings(opt.strategy).get(h["chunk_id"], []):
                if c["chunk_id"] not in have and n_sib < MAX_SIBLINGS:
                    have.add(c["chunk_id"])
                    n_sib += 1
                    blocks.append(Block(f"S{len(blocks) + 1}", c["chunk_id"], c["article_ids"], c["text"], 0.0,
                                        linked=True, via="sibling"))
    if opt.expand_links:
        seen = {a for b in blocks for a in b.article_ids}
        for b in list(blocks[:3]):
            for aid in b.article_ids:
                node = graph().get(aid, {})
                for linked in node.get("parent_provisions", []) + node.get("implementing_provisions", []):
                    if linked not in seen and linked in article_texts() and len(blocks) < opt.top_k + n_sib + MAX_LINKED:
                        seen.add(linked)
                        blocks.append(Block(f"S{len(blocks) + 1}", f"art:{linked}", [linked],
                                            article_texts()[linked], 0.0, linked=True, via="link"))
    if opt.expand_reverse_refs:
        blocks += _reverse_ref_blocks(blocks, len(blocks))
    for b in blocks:
        b.status = _status(b.article_ids, as_of)
    if opt.precedents:
        blocks += _precedent_blocks(question, blocks, len(blocks))
    return blocks


def precedent_candidates(question: str, blocks: list[Block]) -> list[tuple[str, float, list[str]]]:
    """(precedent id, cosine to the question, linking hit articles) for every case linked to a search hit, best first."""
    links: dict[str, list[str]] = {}
    for b in blocks:
        if not b.linked:
            for aid in b.article_ids:
                for pid in graph().get(aid, {}).get("precedents", []):
                    if aid not in links.setdefault(pid, []):
                        links[pid].append(aid)
    scores = precedent_scorer().scores(question, list(links))
    return sorted(((pid, scores[pid], links[pid]) for pid in scores), key=lambda c: (-c[1], c[0]))


def _truncate_holding(holding: str) -> str:
    if len(holding) <= PREC_HOLDING_CHARS:
        return holding
    cut = holding[:PREC_HOLDING_CHARS]
    end = cut.rfind("다.")
    return (cut[:end + 2] if end > 0 else cut) + " …(이하 생략)"


def _precedent_blocks(question: str, blocks: list[Block], start: int) -> list[Block]:
    kept = [c for c in precedent_candidates(question, blocks) if c[1] >= PREC_TAU][:MAX_PRECEDENTS]
    out = []
    for i, (pid, score, via) in enumerate(kept):
        p = precedents()[pid]
        text = p.render()
        text = text[:len(text) - len(p.holding)] + _truncate_holding(p.holding)
        out.append(Block(f"S{start + i + 1}", f"prec:{pid}", [pid], text, score, linked=True, via="precedent",
                         status={"status": "not_applicable", "notes": []}, referenced=via))
    return out


def _reverse_ref_blocks(blocks: list[Block], start: int) -> list[Block]:
    seen = {a for b in blocks for a in b.article_ids}
    cands: dict[str, dict] = {}
    for rank, b in enumerate([b for b in blocks if not b.linked][:3]):
        for aid in b.article_ids:
            for src, cue in graph().get(aid, {}).get("referenced_by_cues", {}).items():
                if cue not in REVERSE_CUES or src in seen or src not in article_texts():
                    continue
                c = cands.setdefault(src, {"targets": [], "cue": cue, "rank": rank})
                if aid not in c["targets"]:
                    c["targets"].append(aid)
                c["cue"] = min(c["cue"], cue, key=REVERSE_CUES.index)
    order = sorted(cands, key=lambda s: (-len(cands[s]["targets"]), REVERSE_CUES.index(cands[s]["cue"]), cands[s]["rank"], s))
    return [Block(f"S{start + i + 1}", f"art:{src}", [src], article_texts()[src], 0.0, linked=True,
                  via="reverse", referenced=cands[src]["targets"]) for i, src in enumerate(order[:MAX_REVERSE])]


def messages(question: str, blocks: list[Block], as_of: str, inject: bool,
             prompt: str = PROMPT_VERSION) -> list[dict]:
    context = "\n\n".join(_render(b, as_of, inject) for b in blocks)
    return [{"role": "system", "content": SYSTEMS[prompt].format(as_of=as_of)},
            {"role": "user", "content": f"[근거]\n{context}\n\n[질문]\n{question}"}]


def _bigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _quote(block: Block, sentences: list[str]) -> str:
    paras = [p for p in block.text.split("\n")[1:] if p.strip() and not re.fullmatch(r"\[\w+\]", p.strip())] or [block.text]
    target = _bigrams(" ".join(sentences))
    return max(paras, key=lambda p: len(_bigrams(p) & target))[:300]


def _article_url(aid: str) -> str:
    law, key = aid.split("#")
    num, _, branch = key.partition("의")
    return f"https://www.law.go.kr/법령/{quote(law)}/제{num}조" + (f"의{branch}" if branch else "")


def _title(aid: str) -> str:
    return f"{aid.split('#')[0]} {_label(aid)}"


def _precedent_citation(b: Block) -> dict:
    p = precedents()[b.article_ids[0]]
    y, m, d = p.decided.split("-")
    return {"source_type": "precedent", "law": "대법원", "article": f"대법원 {y}. {int(m)}. {int(d)}. 선고 {p.case_no} 판결",
            "url": f"https://www.law.go.kr/판례/({quote(p.case_no.split(',')[0].strip())})"}


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
        ref = _precedent_citation(b) if b.via == "precedent" else {
            "source_type": "statute", "law": primary.split("#")[0],
            "article": " · ".join(_label(a) for a in b.article_ids), "url": _article_url(primary)}
        citations.append({
            "source": src, "chunk_id": b.chunk_id, "article_ids": b.article_ids, "law": ref["law"],
            "article": ref["article"], "quote": _quote(b, sents), "url": ref["url"], "source_type": ref["source_type"],
            "status": b.status["status"], "status_notes": b.status["notes"],
        })
    if not citations:
        return "insufficient_context", [], "no_valid_citation"
    return "answered", citations, None


def answer(question: str, opt: Options | None = None, as_of: date | None = None, llm: LLM | None = None,
           include_context: bool = False) -> dict:
    """include_context adds meta["context"] (the rendered blocks the model saw) for grounding checks."""
    opt, t0 = opt or Options(), time.time()
    as_of_s = (as_of or date.today()).isoformat()
    llm = llm or LLM()
    blocks = build_blocks(question, opt, as_of_s)
    retrieval = [{"rank": i + 1, "chunk_id": b.chunk_id, "article_ids": b.article_ids, "score": round(b.score, 4),
                  "linked": b.linked, "via": b.via} for i, b in enumerate(blocks)]
    base_meta = {"prompt_version": opt.prompt, "strategy": opt.strategy, "as_of": as_of_s}

    if not blocks or blocks[0].score < opt.tau:
        return {"status": "insufficient_context", "answer": None, "citations": [], "retrieval": retrieval,
                "meta": {**base_meta, "model": None, "latency_ms": int((time.time() - t0) * 1000),
                         "usage": None, "cost_krw": 0.0, "refusal_reason": "retrieval_below_tau"}}

    text, usage = llm.chat(messages(question, blocks, as_of_s, opt.inject_status, opt.prompt), max_tokens=800)
    status, citations, reason = finalize(text, blocks)
    context = [{"source": b.source, "chunk_id": b.chunk_id, "article_ids": b.article_ids,
                "text": _render(b, as_of_s, opt.inject_status)} for b in blocks] if include_context else None
    return {"status": status, "answer": text if status == "answered" else None, "citations": citations,
            "retrieval": retrieval,
            "meta": {**base_meta, "model": usage["model"], "latency_ms": int((time.time() - t0) * 1000),
                     "usage": {"input": usage["prompt_tokens"], "output": usage["completion_tokens"],
                               "cached_input": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0},
                     "cost_krw": 0.0 if usage.get("cached") else round(cost_of(llm.model, usage), 4),
                     "refusal_reason": reason, "raw_answer": text,
                     "cached": bool(usage.get("cached")), "context": context}}
