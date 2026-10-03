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
(ROOT / "data/train/review_sample_v1.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
opus_path = ROOT / "data/train/review_opus_v1.json"
opus = json.loads(opus_path.read_text())["verdicts"] if opus_path.exists() else {}
codex_path = ROOT / "data/train/review_codex_v1.json"
codex = json.loads(codex_path.read_text())["verdicts"] if codex_path.exists() else {}
views_path = ROOT / "data/train/review_views_v1.json"
views = json.loads(views_path.read_text()) if views_path.exists() else {}
# Disagreement patterns, grouped by hand after reading both models' reasons (tools/summarize_review_views.py).
PATTERN = {'t24': '구별 가능성 vs 내용 일치', 't40': '구별 가능성 vs 내용 일치', 't15': '판례 근거 조문 vs 쟁점 전체의 직접 규정', 't18': '판례 근거 조문 vs 쟁점 전체의 직접 규정', 't25': '같은 결함, 심각도 판단 차이'}
for it in items:
    it["view"] = views.get(it["id"])
    it["pattern"] = PATTERN.get(it["key"])
    it["opus"] = opus.get(it["id"])
    it["codex"] = codex.get(it["id"])
page = (ROOT / "tools/train_review_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(items)} pairs → {sys.argv[1]}")
