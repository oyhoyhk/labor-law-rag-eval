"""Check whether retrieved chunks contain each gold item's evidence articles (M1, no LLM calls).

Usage: uv run python -m eval.retrieval_check [--strategy article|fixed] [--k 5] [--ids g031,l5a01]
"""

import argparse
import json
from datetime import date

from app.ingest.parse import ROOT
from app.rag import Options, build_blocks

GOLD = ROOT / "eval" / "gold" / "gold_v1_1.jsonl"


def check(item: dict, opt: Options) -> dict:
    blocks = build_blocks(item["question"], opt, item.get("as_of") or date.today().isoformat())
    gold = set(item["gold_evidence"])
    found = {}  # gold article id -> first rank / via
    for rank, b in enumerate(blocks, 1):
        for aid in set(b.article_ids) & gold:
            found.setdefault(aid, {"rank": rank, "chunk_id": b.chunk_id,
                                   "via": "reverse" if b.referenced else "linked" if b.linked else "search"})
    searched = [f for f in found.values() if f["via"] == "search"]
    return {
        "id": item["id"], "level": item["level"], "gold": sorted(gold),
        "found": found, "missing": sorted(gold - set(found)),
        "hit_any": bool(searched), "hit_all": not (gold - {a for a, f in found.items() if f["via"] == "search"}),
        "first_rank": min((f["rank"] for f in searched), default=None),
        "n_reverse_blocks": sum(bool(b.referenced) for b in blocks),
        "reverse_chars": sum(len(b.text) for b in blocks if b.referenced),
        "retrieved": [{"rank": r, "chunk_id": b.chunk_id, "article_ids": b.article_ids, "score": round(b.score, 4),
                       "linked": b.linked} for r, b in enumerate(blocks, 1)],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="article", choices=["article", "fixed"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--ids", default="")
    ap.add_argument("--no-links", action="store_true", help="disable delegation-link expansion")
    ap.add_argument("--reverse-refs", action="store_true",
                    help="add articles that reference a top hit with an exception/준용 cue")
    args = ap.parse_args()
    opt = Options(strategy=args.strategy, top_k=args.k, expand_links=not args.no_links,
                  expand_reverse_refs=args.reverse_refs)
    items = [json.loads(l) for l in GOLD.open() if l.strip()]
    if args.ids:
        items = [i for i in items if i["id"] in args.ids.split(",")]
    items = [i for i in items if i["gold_evidence"]]  # OOS items have nothing to retrieve
    rows = [check(i, opt) for i in items]
    for r in rows:
        mark = "ALL " if r["hit_all"] else "SOME" if r["hit_any"] else "MISS"
        linked = sorted(a for a, f in r["found"].items() if f["via"] != "search")
        print(f"{r['id']:<6} {r['level']:<4} {mark} rank={r['first_rank']}  missing={r['missing']}"
              + (f"  linked_only={linked}" if linked else ""))
    n = len(rows)
    mrr = sum(1 / r["first_rank"] for r in rows if r["first_rank"]) / n
    with_links = sum(bool(r["found"]) for r in rows)
    print(f"\n[{args.strategy} k={args.k}] Recall@k(any) {sum(r['hit_any'] for r in rows)}/{n} = "
          f"{sum(r['hit_any'] for r in rows) / n:.2f} · Recall@k(all) {sum(r['hit_all'] for r in rows) / n:.2f} · MRR {mrr:.2f}"
          f" · 위임 확장 포함 {with_links}/{n}")
    by_via = {v: sorted(f"{r['id']}:{a}" for r in rows for a, f in r["found"].items() if f["via"] == v)
              for v in ("linked", "reverse")}
    all_with_links = sum(not r["missing"] for r in rows)
    print(f"gold articles reached only by expansion — 위임 {len(by_via['linked'])} · 역참조 {len(by_via['reverse'])}"
          f" {by_via['reverse']} · Recall@k(all, 확장 포함) {all_with_links}/{n} = {all_with_links / n:.2f}")
    if args.reverse_refs:
        nb = [r["n_reverse_blocks"] for r in rows]
        print(f"역참조 블록 {sum(nb)}개 / {n}문항 (문항당 평균 {sum(nb) / n:.2f}, 추가 문자 평균 "
              f"{sum(r['reverse_chars'] for r in rows) / n:.0f}자)")


if __name__ == "__main__":
    main()
