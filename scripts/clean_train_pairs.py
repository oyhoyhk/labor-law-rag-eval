"""pairs_v1 → pairs_v2: apply the rules derived from the human-confirmed sample (data/train/review_human_v1.json).

  title      prefix the law's common short name (+ 시행령/시행규칙) so the query singles out one article
             ("고충접수ㆍ처리대장" → "남녀고용평등법 시행규칙 고충접수ㆍ처리대장"); deleted articles dropped
  synthetic  drop questions that do not name their law ("이 규칙은…", "이 법에서…") — not distinguishable
  precedent  keep only pairs Opus judged answers ∧ distinct, positives = articles judged core
             (data/train/precedent_judgments_v1.jsonl); unjudged pairs are left out
  all        re-run the gold-similarity leakage guard on the rewritten queries

Usage: uv run python scripts/clean_train_pairs.py
Output: data/train/pairs_v2.jsonl, data/train/pairs_v2.stats.json
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.index import embedder  # noqa: E402

GOLD_SIM = 0.85
SHORT = {"근로기준법": "근로기준법", "최저임금법": "최저임금법", "근로자퇴직급여 보장법": "퇴직급여법",
         "남녀고용평등과 일ㆍ가정 양립 지원에 관한 법률": "남녀고용평등법", "기간제 및 단시간근로자 보호 등에 관한 법률": "기간제법",
         "파견근로자 보호 등에 관한 법률": "파견법", "근로자참여 및 협력증진에 관한 법률": "근로자참여법", "임금채권보장법": "임금채권보장법"}
UNNAMED = re.compile(r"(?:^|\s)(이|본|해당|위의?|그)\s*(법률|법|규칙|영|시행령|시행규칙|조문|조항|규정)(은|는|이|가|에|의|에서|상|을|를|로|$|\s)")


def short_law(aid: str) -> str:
    law = aid.split("#")[0]
    for suffix in (" 시행규칙", " 시행령"):
        if law.endswith(suffix):
            return SHORT[law[: -len(suffix)]] + suffix
    return SHORT[law]


def main() -> None:
    rows = [json.loads(l) for l in (ROOT / "data/train/pairs_v1.jsonl").open()]
    judged = {}
    path = ROOT / "data/train/precedent_judgments_v1.jsonl"
    if path.exists():
        judged = {j["id"]: j for j in map(json.loads, path.open())}
    out, dropped = [], {"synthetic_unnamed": [], "precedent_rejected": 0, "precedent_unjudged": 0, "near_gold": []}
    for r in rows:
        if r["source"] == "title":
            out.append({**r, "query": f"{short_law(r['positives'][0])} {r['query']}", "orig_query": r["query"]})
        elif r["source"] == "synthetic":
            if UNNAMED.search(r["query"]):
                dropped["synthetic_unnamed"].append(r["query"])
            else:
                out.append(r)
        else:
            j = judged.get(r["id"])
            if j is None:
                dropped["precedent_unjudged"] += 1
            elif not j["keep"]:
                dropped["precedent_rejected"] += 1
            else:
                out.append({**r, "positives": j["positives"], "orig_positives": r["positives"]})
    gold = [json.loads(l) for l in (ROOT / "eval/gold/gold_v2.jsonl").open()]
    model = embedder()
    gq = model.encode([g["question"] for g in gold], normalize_embeddings=True)
    rq = model.encode([r["query"] for r in out], normalize_embeddings=True, batch_size=64)
    sims = (rq @ gq.T).max(axis=1)
    final = []
    for r, s in zip(out, sims):
        (dropped["near_gold"].append(r["query"]) if s >= GOLD_SIM else final.append(r))
    (ROOT / "data/train/pairs_v2.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in final))
    stats = {"total": len(final),
             "by_source": {s: sum(r["source"] == s for r in final) for s in ("precedent", "title", "synthetic")},
             "positives": sum(len(r["positives"]) for r in final),
             "articles_covered": len({a for r in final for a in r["positives"]}),
             "dropped": {k: (len(v) if isinstance(v, list) else v) for k, v in dropped.items()},
             "dropped_examples": {k: v[:10] for k, v in dropped.items() if isinstance(v, list)},
             "precedent_judged": len(judged)}
    (ROOT / "data/train/pairs_v2.stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps({k: stats[k] for k in ("total", "by_source", "positives", "articles_covered", "dropped")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
