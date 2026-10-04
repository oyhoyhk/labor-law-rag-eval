"""Per-item report of one run: what RAG retrieved (vs gold evidence) and how the answer was graded.

Usage: uv run python tools/build_item_report_page.py runs/<best run> [runs/<repeat> ...]
Output: tools/item_report_page.html (the first run is shown; the others only add per-item M0 stability)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).with_name("item_report_template.html")


def jl(path: Path) -> dict:
    return {r["id"]: r for r in map(json.loads, path.open()) if r}


def main() -> None:
    runs = [Path(a) for a in sys.argv[1:]]
    gold = jl(ROOT / "eval/gold/gold_v2.jsonl")
    preds, scores = jl(runs[0] / "predictions.jsonl"), jl(runs[0] / "scores.jsonl")
    judg = jl(runs[0] / "judgments.jsonl")
    repeats = [jl(r / "scores.jsonl") for r in runs]
    manifest = json.loads((runs[0] / "manifest.json").read_text())
    items = []
    for i, g in gold.items():
        p, s, j = preds[i], scores[i], judg.get(i, {})
        ev = set(g["gold_evidence"])
        retrieved = [{"rank": r["rank"], "id": r["article_ids"][0] if len(r["article_ids"]) == 1 else ", ".join(r["article_ids"]),
                      "score": r["score"], "via": r["via"], "gold": bool(ev & set(r["article_ids"]))} for r in p["retrieval"]]
        got = {a for r in p["retrieval"] for a in r["article_ids"]}
        searched = {a for r in p["retrieval"] if not r["linked"] for a in r["article_ids"]}
        grade = j.get("grade", {})
        kps = [k for k in grade.get("key_points", []) if k.get("key_point") in g["key_points"]] or grade.get("key_points", [])
        claims = j.get("grounding", {}).get("claims", [])
        items.append({
            "id": i, "level": g["level"], "split": s.get("split"), "question": g["question"], "expected": g["expected_status"],
            "reference": g["reference_answer"], "notes": g.get("notes", ""),
            "status": p["status"], "refusal_reason": p["meta"].get("refusal_reason"), "refusal_mode": s.get("refusal_mode"),
            "m0": s["m0_correct"], "stability": [bool(r[i]["m0_correct"]) for r in repeats],
            "gold": sorted(ev), "found_search": sorted(ev & searched), "found_link": sorted((ev & got) - searched),
            "missing": sorted(ev - got), "recall_all": s.get("m1_recall_all"), "rr": s.get("m1_rr"),
            "retrieved": retrieved, "answer": p["answer"] or p["meta"].get("raw_answer") or "",
            "citations": [c["article_ids"][0] for c in p["citations"]],
            "cit_precision": s.get("m3_citation_precision"), "cit_recall": s.get("m3_citation_recall"),
            "key_points": [{"text": k["key_point"], "ok": k["asserted"], "quote": k.get("quote", "")} for k in kps],
            "asserts_conclusion": grade.get("asserts_conclusion"),
            "unsupported": [c["claim"] for c in claims if not c.get("supported")], "n_claims": len(claims),
        })
    meta = {"run": runs[0].name, "repeats": [r.name for r in runs], "config": manifest["config"],
            "embedding": manifest["embedding"], "model": manifest["model"], "judge": manifest["judge_version"],
            "overall": json.loads((runs[0] / "report.json").read_text())["overall"]}
    data = json.dumps({"meta": meta, "items": items}, ensure_ascii=False).replace("</", "<\\/")
    out = Path(__file__).with_name("item_report_page.html")
    out.write_text(TEMPLATE.read_text().replace("/*__DATA__*/null", data))
    print(out, len(items), "items")


if __name__ == "__main__":
    main()
