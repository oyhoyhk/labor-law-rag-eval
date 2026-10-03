"""Build the sample-audit page for fine-tuning pairs: a stratified random sample with the positive article text.

Usage: uv run python tools/build_train_review_page.py OUT.html
Writes the fixed sample to data/train/review_sample_v1.json and embeds Opus verdicts from
data/train/review_opus_v1.json when present (tools/opus_review_train_pairs.py).
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
# Competing articles for the v2 audit: what the current retriever (whole-article index) returns for the query,
# minus the labelled positives, so a judge can tell whether the query singles out its positive.
from app.rag import retriever  # noqa: E402
ret = retriever("whole")
for it in items:
    pos = {p["id"] for p in it["positives"]}
    comp = [a for h in ret.search(it["query"], 12) for a in h["article_ids"] if a not in pos]
    it["competitors"] = [{"id": a, "text": texts.get(a, "")} for a in dict.fromkeys(comp)][:5]
(ROOT / "data/train/review_sample_v1.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
def load(name: str) -> dict:
    path = ROOT / f"data/train/{name}.json"
    return json.loads(path.read_text()).get("verdicts", json.loads(path.read_text())) if path.exists() else {}


# v2 audit (with competing articles) is primary; v1 kept for comparison.
opus, codex, views = load("review_opus_v2"), load("review_codex_v2"), load("review_views_v2")
notes, notes_codex = load("review_positive_notes_v1"), load("review_positive_notes_codex_v1")
opus_v1, codex_v1 = load("review_opus_v1"), load("review_codex_v1")


def pattern(o: dict, c: dict) -> str | None:
    if not o or not c or o.get("verdict") == c.get("verdict"):
        return None
    if o.get("answers") == c.get("answers") and o.get("distinct") == c.get("distinct"):
        return "같은 사실 판단, 등급 차이"
    return "구별 가능성 판단 차이" if o.get("distinct") != c.get("distinct") else "답변 가능성 판단 차이"


for it in items:
    o, c = opus.get(it["id"]), codex.get(it["id"])
    it.update(opus=o, codex=c, view=views.get(it["id"]), pattern=pattern(o, c), notes=notes.get(it["id"], []), notes_codex=notes_codex.get(it["id"], []),
              v1={"opus": (opus_v1.get(it["id"]) or {}).get("verdict"), "codex": (codex_v1.get(it["id"]) or {}).get("verdict")})
page = (ROOT / "tools/train_review_slides.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(items)} pairs → {sys.argv[1]}")
