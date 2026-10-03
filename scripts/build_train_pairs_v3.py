"""Training data v3: add the two query types the v2 pairs lacked (diagnosed from the fine-tuning results).

  multi  one question whose full answer needs BOTH articles of a graph pair → positives = both
         (law ↔ implementing decree/rule, rule ↔ its exception "…에도 불구하고")
  case   one concrete situation-style question per article ("저는 ~한 상황인데…") → positives = that article

v2 pairs are 1-positive and mostly title/issue/definition-style, while retrieval misses are multi-article and
case-style questions. Gold questions are never used; the gold-similarity guard is re-applied, and a strict
variant drops every row whose positives touch a gold evidence article (to measure how much overlap helps).

Usage: uv run python scripts/build_train_pairs_v3.py [--budget 1000]
Output: data/train/pairs_v3.jsonl (v2 + new), data/train/pairs_v3_strict.jsonl, data/train/pairs_v3.stats.json
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.index import embedder  # noqa: E402
from app.ingest.parse import load_corpus  # noqa: E402
from app.llm import LLM  # noqa: E402

GOLD_SIM = 0.85
MULTI = """다음은 한국 노동법령의 조문 두 개입니다. 두 조문을 **모두** 읽어야 완전히 답할 수 있는, 일반 근로자나 인사 담당자가 실제로 물을 법한 질문 1개를 만드세요.
규칙:
- 구체적인 상황을 담은 자연스러운 구어체, 조문 번호·법령명은 쓰지 않음
- 한 조문만으로는 답의 일부만 나오고, 나머지는 다른 조문에 있어야 함 (예: 법이 원칙을 정하고 시행령이 구체 기준을 정함 / 원칙과 예외)
- 그런 질문을 만들 수 없으면 uses_both를 false로
JSON으로만 답: {{"question": "...", "uses_both": true|false}}

[조문 A]
{a}

[조문 B]
{b}"""
CASE = """다음은 한국 노동법령의 조문입니다. 이 조문이 답이 되는, 구체적인 사정을 설명하며 묻는 사례형 질문 1개를 만드세요.
규칙:
- "저는 ~한 회사에서 ~한 상황인데" 처럼 당사자의 사정·숫자·기간을 담은 구어체 2~3문장
- 조문 번호·법령명은 쓰지 않음, 조문 내용을 그대로 베끼지 않음
- 질문의 답(또는 핵심 근거)이 이 조문에 있어야 함
JSON으로만 답: {{"question": "..."}}

[조문]
{text}"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=1000)
    args = ap.parse_args()
    arts = {f"{a.law}#{a.article_key}": a.render() for a in load_corpus("현행")}
    graph = json.loads((ROOT / "data/processed/provision_graph.json").read_text())["nodes"]
    gold = [json.loads(l) for l in (ROOT / "eval/gold/gold_v2.jsonl").open()]
    gold_ev = {e for g in gold for e in g["gold_evidence"]}

    def is_law(aid):
        return not aid.split("#")[0].endswith(("시행령", "시행규칙"))

    pairs = {(a, i, "delegation") for a, n in graph.items() if a in arts and is_law(a)
             for i in n.get("implementing_provisions", []) if i in arts}
    pairs |= {(a, b, "exception") for a, n in graph.items() if a in arts
              for b, c in n.get("referenced_by_cues", {}).items() if c == "exception" and b in arts}
    substantive = [a for a, t in arts.items() if len(t) >= 60 and "삭제 <" not in t[:120]]
    llm = LLM(budget_krw=args.budget, cache_dir=ROOT / "data/cache/llm")

    def ask(prompt):
        try:
            out, _ = llm.chat([{"role": "user", "content": prompt}], max_tokens=300, json_mode=True)
            return json.loads(out)
        except Exception as e:  # budget stop or malformed reply: skip this item
            return {"error": str(e)[:100]}

    with ThreadPoolExecutor(8) as ex:
        multi = list(ex.map(lambda p: (p, ask(MULTI.format(a=arts[p[0]][:3000], b=arts[p[1]][:3000]))), sorted(pairs)))
        case = list(ex.map(lambda a: (a, ask(CASE.format(text=arts[a][:3000]))), substantive))

    rows = []
    for (a, b, kind), r in multi:
        if r.get("uses_both") and isinstance(r.get("question"), str) and len(r["question"]) >= 10:
            rows.append({"id": f"multi:{kind}:{a}|{b}", "source": f"multi_{kind}", "query": r["question"].strip(),
                         "positives": [a, b]})
    for a, r in case:
        if isinstance(r.get("question"), str) and len(r["question"]) >= 15:
            rows.append({"id": f"case:{a}", "source": "case", "query": r["question"].strip(), "positives": [a]})

    model = embedder()
    gq = model.encode([g["question"] for g in gold], normalize_embeddings=True)
    rq = model.encode([r["query"] for r in rows], normalize_embeddings=True, batch_size=64)
    sims = (rq @ gq.T).max(axis=1)
    new = [r for r, s in zip(rows, sims) if s < GOLD_SIM]
    near = [r["query"] for r, s in zip(rows, sims) if s >= GOLD_SIM]
    v2 = [json.loads(l) for l in (ROOT / "data/train/pairs_v2.jsonl").open()]
    allrows = v2 + new
    strict = [r for r in allrows if not set(r["positives"]) & gold_ev]
    dump = lambda name, rs: (ROOT / "data/train" / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs))
    dump("pairs_v3.jsonl", allrows)
    dump("pairs_v3_strict.jsonl", strict)
    stats = {"v2": len(v2), "new": len(new), "v3": len(allrows), "v3_strict": len(strict),
             "by_source": {s: sum(r["source"] == s for r in allrows) for s in sorted({r["source"] for r in allrows})},
             "multi_candidates": len(multi), "multi_rejected_by_model": sum(1 for _, r in multi if not r.get("uses_both")),
             "errors": sum(1 for _, r in multi + case if "error" in r), "near_gold_dropped": len(near),
             "near_gold_examples": near[:10], "krw": round(llm.spent_krw, 1)}
    (ROOT / "data/train/pairs_v3.stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in stats.items() if k != "near_gold_examples"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
