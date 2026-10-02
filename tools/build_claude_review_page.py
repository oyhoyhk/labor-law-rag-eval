"""Build the confirmation page: review input (answers, retrieval, context) + Claude review verdicts.

Usage: uv run python tools/build_claude_review_page.py OUT.html
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
inp = [json.loads(l) for l in (ROOT / "eval/gold/review_input_v1.jsonl").open()]
rev = {json.loads(l)["item"]: json.loads(l) for l in (ROOT / "eval/gold/claude_review_v1.jsonl").open()}
gold = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval/gold/gold_v1.jsonl").open()}
preds = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval/results/baseline/predictions.jsonl").open()}


def find_spans(text: str, needle: str) -> list[tuple[int, int]]:
    """Whitespace-insensitive occurrences of needle in text, as (start, end) offsets into text."""
    chars = [re.escape(c) for c in needle if not c.isspace()]
    if len(chars) < 4:
        return []
    return [(m.start(), m.end()) for m in re.finditer(r"\s*".join(chars), text)]


def merge(spans):
    out = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def marks(item_id: str, blocks: list[str]) -> list[dict]:
    """Per context block: spans of gold evidence literals and of the passages the answer quoted."""
    literals = [alt for alts in gold[item_id].get("key_point_literals", []) for alt in alts]
    quotes = {c["source"]: c["quote"] for c in preds[item_id]["citations"]}
    out = []
    for n, text in enumerate(blocks, 1):
        g = merge([sp for lit in literals for sp in find_spans(text, lit)])
        q = merge(find_spans(text, quotes[f"S{n}"])) if f"S{n}" in quotes else []
        out.append({"gold": g, "cited": q})
    return out


items = [{**i, "review": rev[i["id"]], "marks": marks(i["id"], i["context"])} for i in inp]
page = (ROOT / "tools/claude_review_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(items)} items → {sys.argv[1]}")
