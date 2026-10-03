"""Build (query, positive article) pairs for fine-tuning the retrieval embedder — never from the gold set.

Sources
  precedent  판시사항 issue (court-written) → the precedent's 참조조문 corpus articles
  title      조 제목 → the article
  synthetic  Luna writes 2 plain-language questions per article → that article

Leakage guards
  - precedents used by gold items (evidence or case) are excluded
  - any query whose KURE cosine to a gold question is ≥ GOLD_SIM is dropped (near-duplicates of eval questions)

Usage: uv run python scripts/build_train_pairs.py [--no-synthetic] [--budget 700]
Output: data/train/pairs_v1.jsonl, data/train/pairs_v1.stats.json
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.index import embedder  # noqa: E402
from app.ingest.parse import load_corpus  # noqa: E402
from app.ingest.precedent import load_precedents, precedent_id  # noqa: E402
from app.llm import LLM  # noqa: E402

OUT = ROOT / "data" / "train"
GOLD_SIM = 0.85
MIN_CHARS = 60
SYNTH_PROMPT = """다음은 한국 노동법령의 조문입니다. 이 조문을 읽은 적 없는 일반 근로자나 인사 담당자가 실제로 물을 법한 질문 2개를 만드세요.
규칙:
- 질문의 답이 이 조문 안에 있어야 함
- 조문 번호·법령명을 질문에 쓰지 않음, 구체적인 상황을 담은 자연스러운 구어체
- 두 질문은 조문의 서로 다른 내용을 물음
JSON으로만 답: {{"questions": ["...", "..."]}}

[조문]
{text}"""


def split_issues(issues: str) -> list[str]:
    parts = [re.sub(r"^\[\d+\]\s*", "", p.strip(" \n/")) for p in re.split(r"\s/\s|\n", issues)]
    return [p for p in parts if len(p) >= 15]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-synthetic", action="store_true")
    ap.add_argument("--budget", type=float, default=700)
    args = ap.parse_args()

    gold = [json.loads(l) for l in (ROOT / "eval/gold/gold_v2.jsonl").open()]
    gold_prec = {e for g in gold for e in g["gold_evidence"] if e.startswith("판례#")}
    gold_prec |= {precedent_id(g["case"]["case_no"]) for g in gold if g.get("case")}
    articles = {f"{a.law}#{a.article_key}": a for a in load_corpus("현행")}
    graph = json.loads((ROOT / "data/processed/provision_graph.json").read_text())
    precs = load_precedents()

    rows = []
    # precedent: each 판시사항 issue → all corpus articles the precedent cites (multi-positive)
    for pid, meta in graph["precedents"].items():
        pos = [a for a in meta["articles"] if a in articles]
        if pid in gold_prec or not pos or pid not in precs:
            continue
        for k, q in enumerate(split_issues(precs[pid].issues)):
            rows.append({"id": f"prec:{pid}:{k}", "source": "precedent", "query": q, "positives": pos})
    # title: 조 제목 → article
    for aid, a in articles.items():
        m = re.search(r"\(([^)]+)\)", a.label or "")
        if m and "삭제" not in a.render()[:80]:
            rows.append({"id": f"title:{aid}", "source": "title", "query": m.group(1), "positives": [aid]})
    # synthetic: 2 questions per substantive article
    spent = 0.0
    if not args.no_synthetic:
        llm = LLM(budget_krw=args.budget, cache_dir=ROOT / "data/cache/llm")
        targets = [(aid, a.render()) for aid, a in articles.items()
                   if len(a.render()) >= MIN_CHARS and "삭제 <" not in a.render()[:120]]

        def gen(item):
            aid, text = item
            try:
                out, _ = llm.chat([{"role": "user", "content": SYNTH_PROMPT.format(text=text[:3000])}],
                                  max_tokens=400, json_mode=True)
                return aid, json.loads(out).get("questions", [])[:2]
            except Exception as e:  # budget stop or a malformed reply: skip the article, keep the rest
                return aid, {"error": str(e)[:120]}

        with ThreadPoolExecutor(8) as ex:
            results = list(ex.map(gen, targets))
        errors = [aid for aid, qs in results if isinstance(qs, dict)]
        for aid, qs in results:
            if isinstance(qs, list):
                for k, q in enumerate(qs):
                    if isinstance(q, str) and len(q) >= 8:
                        rows.append({"id": f"syn:{aid}:{k}", "source": "synthetic", "query": q.strip(),
                                     "positives": [aid]})
        spent = llm.spent_krw
        print(f"synthetic: {len(targets)} articles, {len(errors)} errors, {spent:.1f} KRW")

    # leakage guard: drop near-duplicates of gold questions
    model = embedder()
    gq = model.encode([g["question"] for g in gold], normalize_embeddings=True)
    rq = model.encode([r["query"] for r in rows], normalize_embeddings=True, batch_size=64)
    sims = rq @ gq.T
    kept, dropped = [], []
    for r, row_sims in zip(rows, sims):
        j = int(np.argmax(row_sims))
        (dropped if row_sims[j] >= GOLD_SIM else kept).append({**r, "max_gold_sim": round(float(row_sims[j]), 3),
                                                               "nearest_gold": gold[j]["id"]})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pairs_v1.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept))
    stats = {"total": len(kept), "by_source": {s: sum(r["source"] == s for r in kept) for s in
                                              ("precedent", "title", "synthetic")},
             "dropped_near_gold": [{"id": r["id"], "query": r["query"], "nearest_gold": r["nearest_gold"],
                                    "sim": r["max_gold_sim"]} for r in dropped],
             "excluded_gold_precedents": sorted(gold_prec), "gold_sim_threshold": GOLD_SIM, "synthetic_krw": spent}
    (OUT / "pairs_v1.stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in stats.items() if k in ("total", "by_source")}, ensure_ascii=False),
          f"dropped {len(dropped)} near-gold")


if __name__ == "__main__":
    main()
