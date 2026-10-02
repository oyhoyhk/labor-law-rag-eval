"""Build the confirmation page: review input (answers, retrieval, context) + Claude review verdicts.

Usage: uv run python tools/build_claude_review_page.py OUT.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
inp = [json.loads(l) for l in (ROOT / "eval/gold/review_input_v1.jsonl").open()]
rev = {json.loads(l)["item"]: json.loads(l) for l in (ROOT / "eval/gold/claude_review_v1.jsonl").open()}
items = [{**i, "review": rev[i["id"]]} for i in inp]
page = (ROOT / "tools/claude_review_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(items)} items → {sys.argv[1]}")
