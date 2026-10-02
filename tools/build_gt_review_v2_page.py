"""Build the human-confirmation page for the 39 gold v2 additions: evidence text with key-point literals marked,
effectivity status, precedent holdings, and the independent model review.

Usage: uv run python tools/build_gt_review_v2_page.py ITEMS.jsonl OUT.html
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ingest.parse import load_corpus  # noqa: E402
from app.ingest.provision import status_at  # noqa: E402
from eval.tags import item_tags  # noqa: E402

AS_OF = "2026-10-01"
corpus = {f"{a.law}#{a.article_key}": a.render() for a in load_corpus("현행")}
graph = json.loads((ROOT / "data/processed/provision_graph.json").read_text())["nodes"]


def holding(case_no: str) -> str:
    path = next((ROOT / "data/raw/precedents").glob(case_no.split(",")[0].strip() + "*.xml"), None)
    if not path:
        return ""
    text = ET.parse(path).getroot().findtext("판결요지") or ""
    return re.sub(r"<br\s*/?>", "\n", text).strip()


def evidence(aid: str, literals: list[list[str]]) -> dict:
    node = graph.get(aid, {})
    st = status_at(node, AS_OF) if node else {"status": "in_force", "notes": []}
    return {"id": aid, "status": st["status"], "notes": st["notes"], "text": corpus.get(aid, "(현행 코퍼스에 없음)"),
            "pending": [{"effective": p["effective"], "changed": p.get("changed_paragraphs") or []}
                        for p in node.get("pending", []) if p["effective"] > AS_OF],
            "marks": [x for alts in literals for x in alts]}


items = []
for l in Path(sys.argv[1]).open():
    it = json.loads(l)
    case = it.get("case") or {}
    items.append({
        "key": it["id"], "id": it["id"], "level": it["level"], "target": it.get("target"), "tags": item_tags(it),
        "expected": it["expected_status"], "recent": it["recent_amendment"], "question": it["question"],
        "key_points": it["key_points"], "reference": it["reference_answer"], "notes": it["notes"],
        "review": it.get("review_v2"), "probe": it.get("probe_terms", []),
        "case_no": case.get("case_no"), "decided": case.get("decided"), "holding": case.get("holding_summary"),
        "reason": case.get("classification_reason"), "holding_ref": case.get("holding_ref"),
        "yoji": holding(case["case_no"]) if case else "",
        "evidence": [evidence(a, it["key_point_literals"]) for a in it["gold_evidence"]]})

page = (ROOT / "tools/gt_review_v2_page.html").read_text()
Path(sys.argv[2]).write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(items)} items → {sys.argv[2]}")
