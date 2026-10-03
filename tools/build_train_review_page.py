"""Build the sample-audit page for fine-tuning pairs: a stratified random sample with the positive article text.

Usage: uv run python tools/build_train_review_page.py OUT.html
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ingest.parse import load_corpus  # noqa: E402

SAMPLE = {"precedent": 15, "synthetic": 15, "title": 10}
SEED = 7

rows = [json.loads(l) for l in (ROOT / "data/train/pairs_v1.jsonl").open()]
texts = {f"{a.law}#{a.article_key}": a.render() for a in load_corpus("현행")}
rng = random.Random(SEED)
items = []
for src, n in SAMPLE.items():
    for r in rng.sample([r for r in rows if r["source"] == src], n):
        items.append({"id": r["id"],
                      "source": src, "query": r["query"],
                      "positives": [{"id": a, "text": texts.get(a, "")} for a in r["positives"]]})
rng.shuffle(items)
for k, it in enumerate(items):  # db doc ids must be ASCII
    it["key"] = f"t{k + 1:02d}"
page = (ROOT / "tools/train_review_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(items)} pairs → {sys.argv[1]}")
