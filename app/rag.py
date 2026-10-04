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

from app import hybrid
from app.index import ENCODE_LOCK, INDEX_DIR, PrecedentScorer, Retriever
from app.ingest.precedent import load_precedents
from app.ingest.provision import GRAPH, status_at
from app.llm import LLM, SEED, cost_of

PROMPT_VERSION = "gen-v1"  # default generation prompt
PROMPT_VERSION_PARTIAL = "gen-v2-partial"  # adds a partial-answer mode between full answer and refusal
PROMPT_VERSION_PRECEDENT = "gen-v3-precedent"  # statute first, then linked Supreme Court holdings; set by --precedents
PROMPT_VERSION_CHECKLIST = "gen-v4-checklist"  # gen-v3-precedent + a legal-answer checklist; set by --checklist
# Suffix for --fewshot-dev (app/fewshot.py, deliberate eval-set leakage demo): base prompt + nearest dev examples.
FEWSHOT_SUFFIX = "+fewshot-dev"
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

# Generalization A/B #1 (docs/plans/2026-10-03-generalization-ab-plan.md): the items every legal answer should check,
# derived from failure types (missing exception status, delegation, pending amendment, general rule), not from items.
CHECKLIST_RULE = """
답변하기 전에 근거 블록에서 다음을 차례로 확인하고, 질문과 관련된 것은 빠짐없이 답변에 쓴다.
(가) 질문에 적용되는 원칙(누가, 무엇을, 얼마나, 언제까지)
(나) 그 원칙의 예외·단서가 근거 블록에 있는지. 질문이 예외 해당 여부를 묻는데 예외가 없으면 예외가 없다는 점
(다) 세부 기준을 대통령령·고용노동부령 등 하위 법령에 위임했는지와, 하위 법령 블록이 있으면 그 기준
(라) 시행 예정 개정이 질문의 결론을 바꾸는지. 바꾸면 바뀌는 내용, 공포일, 시행일, 기준일 현재 적용 여부
(마) 질문이 특수한 경우를 물으면, 비교 기준이 되는 일반적인 경우의 기준"""
SYSTEM_CHECKLIST = SYSTEM_PRECEDENT.replace("\n8. 한국어 합니다체로 간결하게 답한다.", "\n8. 한국어 합니다체로 답한다." + CHECKLIST_RULE)

SYSTEMS = {PROMPT_VERSION: SYSTEM, PROMPT_VERSION_PARTIAL: SYSTEM_PARTIAL, PROMPT_VERSION_PRECEDENT: SYSTEM_PRECEDENT,
           PROMPT_VERSION_CHECKLIST: SYSTEM_CHECKLIST}

VERIFY_SYSTEM = """당신은 한국 노동법령 답변 검토자입니다. [근거] 블록, [질문], [초안 답변]을 받습니다.
초안을 [근거] 블록과 대조해 다음을 고친 최종 답변만 출력하세요.
1. 근거 블록에 있는데 질문에 답하는 데 필요한 내용(원칙, 예외·단서 유무, 위임된 하위 법령의 기준, 시행 예정 개정의 내용·공포일·시행일)이 빠졌으면 추가한다.
2. 근거 블록이 뒷받침하지 않는 문장은 삭제한다.
3. 사실을 말하는 모든 문장 끝에 근거 블록 번호를 [S1]처럼 붙인다. 초안의 형식(판례 인용 방식, 합니다체)을 유지한다.
4. 고칠 것이 없으면 초안을 그대로 출력한다. 설명이나 검토 의견은 쓰지 않는다."""

MERGE_SYSTEM = """당신은 한국 노동법령 답변 편집자입니다. [근거] 블록, [질문], 같은 질문에 대한 [초안] 여러 개를 받습니다.
초안들을 종합해 최종 답변 하나만 출력하세요.
1. 초안들 중 어느 하나에라도 있고 근거 블록이 뒷받침하는 내용은 빠짐없이 포함한다.
2. 근거 블록이 뒷받침하지 않거나 초안끼리 충돌하는 내용은 근거 블록에 맞는 쪽만 남긴다.
3. 사실을 말하는 모든 문장 끝에 근거 블록 번호를 [S1]처럼 붙인다. 합니다체로 쓴다.
4. 초안 과반이 첫 줄을 "[정보 부족]"으로 썼으면 최종 답변도 첫 줄을 정확히 "[정보 부족]"으로 쓰고 무엇이 없는지만 한 문장으로 쓴다."""

REWRITE_SYSTEM = """한국 노동법령 검색용 질의를 만듭니다. 사용자 질문을 읽고, 답이 될 법령 조문을 찾기 위한 검색 질의 2~3개를 만드세요.
- 각 질의는 법령 조문에 쓰이는 용어로 쓴 짧은 문장 (예: "육아휴직 종료 후 같은 업무 또는 같은 수준의 임금을 지급하는 직무 복귀")
- 질문에 쟁점이 여러 개면 쟁점마다 하나씩
- 법령명이나 조문 번호를 추측해 쓰지 않는다
JSON으로만 답: {"queries": ["...", "..."]}"""
REWRITE_N = 30  # dense candidates per query before RRF
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
RERANK_N = 30  # dense candidates re-scored by the cross-encoder
RERANK_MAX_TOKENS = 1024
DIRECT_PRECEDENTS = 2  # --precedent-search: cases found by cosine over all precedents, on top of linked ones


@dataclass
class Options:
    # one chunk per 조, embedded with Qwen3-Embedding-4B (adopted 2026-10-04; "whole" = same chunks with KURE-v1,
    # "article" splits long 조 at 항·호); top 10 (adopted 2026-10-04, docs/findings/2026-10-03-embedding-finetune.md §7)
    strategy: str = "whole@Qwen3-Embedding-4B"
    top_k: int = 10
    inject_status: bool = True  # H4 switch
    expand_links: bool = True
    tau: float = TAU
    include_siblings: bool = True  # add the other chunks of a split article (no-op for "whole", which never splits)
    expand_reverse_refs: bool = False
    prompt: str = PROMPT_VERSION  # key of SYSTEMS
    precedents: bool = True  # add linked Supreme Court precedents; switches the prompt to gen-v3-precedent
    fewshot_dev: bool = False  # OVERFITTING DEMO ONLY (app/fewshot.py): never enable in production
    hybrid: bool = False  # dense + character-bigram BM25 fused by RRF (app/hybrid.py)
    # Generalization A/B (docs/plans/2026-10-03-generalization-ab-plan.md), all off by default
    checklist: bool = False  # 1: legal-answer checklist in the prompt
    pending_detail: bool = False  # 2: show the changed 호 of pending amendments, not just the paragraph lead
    verify: bool = False  # 3: second call that checks the draft against the context and rewrites it
    self_consistency: int = 0  # 4: n drafts (different seeds, temperature 0.7) merged by one more call
    query_rewrite: bool = False  # 5: LLM rewrites the question into legal-term queries, fused with RRF
    rerank: bool = False  # 6: cross-encoder re-scores the top RERANK_N dense hits
    precedent_search: bool = False  # 7: precedents found directly over all 400 cases, besides linked ones

    def __post_init__(self):
        if self.precedents:
            self.prompt = PROMPT_VERSION_CHECKLIST if self.checklist else PROMPT_VERSION_PRECEDENT
        if self.fewshot_dev and not self.prompt.endswith(FEWSHOT_SUFFIX):
            self.prompt += FEWSHOT_SUFFIX


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


def _render(b: Block, as_of: str, inject: bool, pending_detail: bool = False) -> str:
    if b.via == "precedent":
        if not b.referenced:  # --precedent-search hit, not linked to a retrieved article
            return f"[{b.source}] (질문과 유사한 대법원 판례)\n{b.text}"
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
                    if pending_detail and p.get("changed_detail"):
                        lines.append(f"[{p['effective']} 시행 예정 개정 내용 (공포 {p['promulgated']}, 바뀌는 항과 신설·개정되는 호)]\n"
                                     + "\n".join(p["changed_detail"]))
                    else:
                        lines.append(f"[{p['effective']} 시행 예정 개정 내용] " + " / ".join(p["changed_paragraphs"]))
    lines.append(b.text)
    return "\n".join(lines)


@lru_cache(maxsize=1)
def reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANK_MODEL, max_length=RERANK_MAX_TOKENS)


def rewrite_queries(question: str, llm: LLM) -> list[str]:
    try:
        text, _ = llm.chat([{"role": "system", "content": REWRITE_SYSTEM}, {"role": "user", "content": question}],
                           max_tokens=300, json_mode=True)
        qs = json.loads(text).get("queries", [])
        return [q for q in qs if isinstance(q, str) and q.strip()][:3]
    except (json.JSONDecodeError, AttributeError):
        return []


def _search(question: str, opt: Options, llm: LLM | None) -> tuple[list[dict], dict]:
    """Search hits (score = cosine to the original question, for the τ gate) and extra meta."""
    r = retriever(opt.strategy)
    if opt.hybrid:
        return hybrid.search(r, question, opt.top_k), {}
    if not (opt.query_rewrite or opt.rerank):
        return r.search(question, opt.top_k), {}
    base = r.search(question, max(REWRITE_N, RERANK_N))
    cos = {h["chunk_id"]: h["score"] for h in base}
    meta: dict = {}
    if opt.query_rewrite:
        queries = rewrite_queries(question, llm or LLM())
        meta["rewritten_queries"] = queries
        rankings = [[h["chunk_id"] for h in base[:REWRITE_N]]] + [[h["chunk_id"] for h in r.search(q, REWRITE_N)] for q in queries]
        by_id = {c["chunk_id"]: c for c in r.chunks}
        fused = hybrid.rrf(rankings, [1.0] * len(rankings), hybrid.RRF_K)
        cand = [by_id[cid] for cid, _ in fused]
    else:
        cand = base
    if opt.rerank:
        cand = cand[:RERANK_N]
        with ENCODE_LOCK:
            rs = reranker().predict([(question, c["text"]) for c in cand], batch_size=8)
        cand = [c for _, c in sorted(zip(rs, cand), key=lambda x: -float(x[0]))]
        meta["rerank_scores"] = sorted((round(float(x), 4) for x in rs), reverse=True)[:opt.top_k]
    out = []
    for c in cand[:opt.top_k]:
        s = cos.get(c["chunk_id"])
        if s is None:  # outside the original-question candidates: cosine from the stored vector
            with ENCODE_LOCK:
                q = r.model.encode([r.query_prefix + question], normalize_embeddings=True, convert_to_numpy=True)[0]
            s = float(r.index.reconstruct(r.chunks.index(c)) @ q)
        out.append({**c, "score": s})
    return out, meta


def build_blocks(question: str, opt: Options, as_of: str, llm: LLM | None = None, meta: dict | None = None) -> list[Block]:
    hits, extra = _search(question, opt, llm)
    if meta is not None:
        meta.update(extra)
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
        blocks += _precedent_blocks(question, blocks, len(blocks), opt.precedent_search)
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


def _precedent_blocks(question: str, blocks: list[Block], start: int, direct: bool = False) -> list[Block]:
    kept = [c for c in precedent_candidates(question, blocks) if c[1] >= PREC_TAU][:MAX_PRECEDENTS]
    if direct:  # A/B #7: also the closest cases over the whole set, linked or not
        have = {c[0] for c in kept}
        scores = precedent_scorer().scores(question, list(precedents()))
        best = sorted((pid for pid in scores if pid not in have and scores[pid] >= PREC_TAU), key=lambda p: (-scores[p], p))
        kept += [(pid, scores[pid], []) for pid in best[:DIRECT_PRECEDENTS]]
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
             prompt: str = PROMPT_VERSION, pending_detail: bool = False) -> list[dict]:
    context = "\n\n".join(_render(b, as_of, inject, pending_detail) for b in blocks)
    system = SYSTEMS[prompt.removesuffix(FEWSHOT_SUFFIX)].format(as_of=as_of)
    if prompt.endswith(FEWSHOT_SUFFIX):
        from app import fewshot  # imported only when the leakage demo is on
        system += "\n" + fewshot.section(question)
    return [{"role": "system", "content": system},
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


def _followup(system: str, msgs: list[dict], question: str, drafts: str) -> list[dict]:
    """A second-pass request over the same context: msgs[1] holds "[근거]…[질문]…"."""
    return [{"role": "system", "content": system},
            {"role": "user", "content": f"{msgs[1]['content']}\n\n{drafts}"}]


def answer(question: str, opt: Options | None = None, as_of: date | None = None, llm: LLM | None = None,
           include_context: bool = False) -> dict:
    """include_context adds meta["context"] (the rendered blocks the model saw) for grounding checks."""
    opt, t0 = opt or Options(), time.time()
    as_of_s = (as_of or date.today()).isoformat()
    llm = llm or LLM()
    extra: dict = {}
    blocks = build_blocks(question, opt, as_of_s, llm, extra)
    retrieval = [{"rank": i + 1, "chunk_id": b.chunk_id, "article_ids": b.article_ids, "score": round(b.score, 4),
                  "linked": b.linked, "via": b.via} for i, b in enumerate(blocks)]
    base_meta = {"prompt_version": opt.prompt, "strategy": opt.strategy, "as_of": as_of_s, **extra}

    if not blocks or blocks[0].score < opt.tau:
        return {"status": "insufficient_context", "answer": None, "citations": [], "retrieval": retrieval,
                "meta": {**base_meta, "model": None, "latency_ms": int((time.time() - t0) * 1000),
                         "usage": None, "cost_krw": 0.0, "refusal_reason": "retrieval_below_tau"}}

    msgs = messages(question, blocks, as_of_s, opt.inject_status, opt.prompt, opt.pending_detail)
    costs = []  # every generation call of this item (self-consistency / verify make several)

    def call(m, **kw):
        t, u = llm.chat(m, **kw)
        costs.append(0.0 if u.get("cached") else cost_of(llm.model, u))
        return t, u
    if opt.self_consistency:
        drafts = [call(msgs, max_tokens=800, seed=SEED + i, temperature=0.7)[0] for i in range(opt.self_consistency)]
        text, usage = call(_followup(MERGE_SYSTEM, msgs, question,
                                     "\n\n".join(f"[초안 {i + 1}]\n{d}" for i, d in enumerate(drafts))), max_tokens=900)
        extra["drafts"] = drafts
    else:
        text, usage = call(msgs, max_tokens=800)
    if opt.verify and not text.strip().startswith(REFUSAL):
        extra["draft"] = text
        text, usage = call(_followup(VERIFY_SYSTEM, msgs, question, f"[초안 답변]\n{text}"), max_tokens=900)
    status, citations, reason = finalize(text, blocks)
    context = [{"source": b.source, "chunk_id": b.chunk_id, "article_ids": b.article_ids,
                "text": _render(b, as_of_s, opt.inject_status, opt.pending_detail)} for b in blocks] if include_context else None
    return {"status": status, "answer": text if status == "answered" else None, "citations": citations,
            "retrieval": retrieval,
            "meta": {**base_meta, "model": usage["model"], "latency_ms": int((time.time() - t0) * 1000),
                     "usage": {"input": usage["prompt_tokens"], "output": usage["completion_tokens"],
                               "cached_input": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0},
                     "cost_krw": round(sum(costs), 4),
                     "refusal_reason": reason, "raw_answer": text, **extra,
                     "cached": bool(usage.get("cached")), "context": context}}
