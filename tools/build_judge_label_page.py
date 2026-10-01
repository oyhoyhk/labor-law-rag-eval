"""Build the human-labeling page: frozen sample + retrieval provenance from the sample's source run.

Usage: uv run python tools/build_judge_label_page.py OUT.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sample = json.loads((ROOT / "eval/gold/human_label_sample_v1.json").read_text())
preds = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "runs" / sample["source_run"] / "predictions.jsonl").open()}
gold = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval/gold/gold_v1.jsonl").open()}

items = []
for it in sample["items"]:
    p, g = preds[it["id"]], set(gold[it["id"]]["gold_evidence"])
    cited = {c["source"] for c in p["citations"]}
    # Context blocks are numbered in retrieval order: block S{rank} is retrieval row `rank`.
    items.append({**it, "retrieval": [
        {"source": f"S{r['rank']}", "rank": r["rank"], "chunk_id": r["chunk_id"], "score": r["score"], "linked": r["linked"],
         "cited": f"S{r['rank']}" in cited, "gold": bool(g & set(r["article_ids"]))} for r in p["retrieval"]]})

page = (ROOT / "tools/judge_label_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(items)} items → {sys.argv[1]}")
