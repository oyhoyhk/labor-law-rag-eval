"""Deterministic checks for a gold-set draft (no LLM calls).

Usage: uv run python scripts/verify_gold.py [path]
Exits non-zero if any item FAILs.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ingest.parse import load_corpus  # noqa: E402
from app.ingest.provision import status_at  # noqa: E402

DEFAULT = ROOT / "eval/gold/gold_v2.jsonl"
GRAPH = ROOT / "data/processed/provision_graph.json"
AS_OF = "2026-10-01"
EXPECTED_COUNTS = {"L1": 10, "L2": 19, "L3": 23, "L4": 15, "OOS": 8, "L5a": 8, "L5b": 9, "SUM": 8}
V1_1_COUNTS = {"L1": 10, "L2": 11, "L3": 10, "L4": 7, "OOS": 4, "L5a": 8, "L5b": 6, "SUM": 5}
V1_COUNTS = {"L1": 10, "L2": 11, "L3": 10, "L4": 7, "OOS": 4, "L5a": 8, "L5b": 6}
DRAFT_COUNTS = {"L1": 10, "L2": 10, "L3": 10, "L4": 7, "OOS": 4}
CASES = ROOT / "data/raw/precedents"
REQUIRED = ["id", "level", "question", "expected_status", "as_of", "gold_evidence", "key_points",
            "key_point_literals", "reference_answer", "recent_amendment", "notes"]


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def l4_haystack(node: dict) -> str:
    parts = []
    for p in node["pending"]:
        cp = p.get("changed_paragraphs") or []
        parts += cp if isinstance(cp, list) else [str(cp)]
        parts += [p.get("new_text", ""), p.get("effective", ""), p.get("promulgated", "")]
    for s in node["sunsets"]:
        parts += [s.get("clause", ""), s.get("until", "")]
    return "\n".join(parts)


def main(path: Path) -> int:
    items = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    corpus = {f"{a.law}#{a.article_key}": a for a in load_corpus("현행")}
    graph = json.loads(GRAPH.read_text())["nodes"]
    corpus_norm = [(aid, norm(a.render())) for aid, a in corpus.items()]

    global_errors = []
    ids = Counter(i.get("id") for i in items)
    if dups := [k for k, v in ids.items() if v > 1]:
        global_errors.append(f"duplicate ids: {dups}")
    counts = Counter(i.get("level") for i in items)
    expected = (DRAFT_COUNTS if "draft" in path.name else V1_COUNTS if path.name == "gold_v1.jsonl"
                else V1_1_COUNTS if path.name == "gold_v1_1.jsonl" else EXPECTED_COUNTS)
    if dict(counts) != expected:
        global_errors.append(f"level counts {dict(counts)} != {expected}")

    rows, n_fail = [], 0
    for it in items:
        errs, info = [], []
        missing = [k for k in REQUIRED if k not in it]
        if missing:
            errs.append(f"missing fields {missing}")
        lvl, ev = it.get("level"), it.get("gold_evidence", [])
        kps, lits = it.get("key_points", []), it.get("key_point_literals", [])
        if it.get("as_of") != AS_OF:
            errs.append("as_of")

        if lvl in ("L5a", "L5b"):
            case_no = it.get("case", {}).get("case_no", "")
            if not any(CASES.glob(case_no.split(",")[0].strip() + "*.xml")):
                errs.append(f"precedent XML missing for {case_no}")
            want = "answered" if lvl == "L5a" else "insufficient_context"
            if it.get("expected_status") != want:
                errs.append(f"{lvl} must be {want}")
            if lvl == "L5a" and not it.get("key_points"):
                errs.append("L5a needs key_points")
            unknown = [aid for aid in ev if aid not in corpus]
            if unknown:
                errs.append(f"unknown evidence ids {unknown}")
            info.append(f"case {case_no}")
        elif lvl == "OOS":
            if it.get("expected_status") != "insufficient_context":
                errs.append("OOS must be insufficient_context")
            if ev or kps or lits:
                errs.append("OOS must have empty evidence/key_points/literals")
            for term in it.get("probe_terms", []):
                hits = [aid for aid, txt in corpus_norm if norm(term) in txt]
                info.append(f"grep '{term}': {len(hits)} hit(s) {hits[:3]}")
        else:
            if it.get("expected_status") != "answered":
                errs.append("expected_status should be answered")
            if not ev:
                errs.append("empty gold_evidence")
            if lvl in ("L3",) and len(ev) < 2:
                errs.append("L3 needs >=2 evidence articles")
            if len(kps) != len(lits) or not kps:
                errs.append(f"key_points({len(kps)}) / literals({len(lits)}) mismatch")
            hay = []
            for aid in ev:
                if aid in corpus:
                    hay.append(norm(corpus[aid].render()))
                elif aid not in graph:
                    errs.append(f"unknown evidence id {aid}")
                if lvl == "L4" and aid in graph:
                    hay.append(norm(l4_haystack(graph[aid])))
            if lvl == "L4":
                sts = {aid: status_at(graph[aid], AS_OF)["status"] for aid in ev if aid in graph}
                info.append(f"status {sts}")
                if not any(s != "in_force" for s in sts.values()):
                    errs.append("L4 item has no evidence with non-in_force status")
            for k, alts in enumerate(lits):
                if not any(norm(alt) in h for alt in alts for h in hay):
                    errs.append(f"kp{k + 1} literal not found: {alts}")

        ok = not errs
        n_fail += not ok
        rows.append((it.get("id"), lvl, "PASS" if ok else "FAIL", "; ".join(errs + info)))

    print(f"{'id':<6}{'level':<6}{'result':<7}detail")
    for r in rows:
        print(f"{r[0]:<6}{r[1]:<6}{r[2]:<7}{r[3]}")

    l13 = [i for i in items if i["level"] in ("L1", "L2", "L3")]
    target = [i for i in l13 if i["recent_amendment"]
              or any(e.split("#")[0].endswith(("시행령", "시행규칙")) for e in i["gold_evidence"])]
    print(f"\nL1-L3 recent-or-decree share: {len(target)}/{len(l13)} = {len(target) / max(len(l13), 1):.0%}")
    print(f"counts: {dict(counts)}")
    for e in global_errors:
        print("GLOBAL FAIL:", e)
    print(f"{len(rows) - n_fail} PASS / {n_fail} FAIL")
    return 1 if (n_fail or global_errors) else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT))
