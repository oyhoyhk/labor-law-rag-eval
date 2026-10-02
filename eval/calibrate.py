"""Judge vs human agreement on the frozen labeling sample.

Usage:
  uv run python -m eval.calibrate                      # labels: eval/gold/human_labels_v1.jsonl
  uv run python -m eval.calibrate --judgments runs/<run>/judgments.jsonl
Adoption rule (docs/design.md §3.3): Cohen's κ ≥ 0.6 on key points and on claim support.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "eval" / "gold" / "human_label_sample_v1.json"
LABELS = ROOT / "eval" / "gold" / "human_labels_v1.jsonl"
OUT = ROOT / "eval" / "results" / "judge_calibration.json"
KAPPA_MIN = 0.6


def cohen_kappa(a: list[bool], b: list[bool]) -> float | None:
    """Binary Cohen's κ. None when chance agreement is 1 (both raters constant and equal)."""
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def binary_report(human: list[bool], judge: list[bool], positive: str) -> dict:
    tp = sum(h and j for h, j in zip(human, judge))
    fp = sum((not h) and j for h, j in zip(human, judge))
    fn = sum(h and (not j) for h, j in zip(human, judge))
    tn = len(human) - tp - fp - fn
    return {"n": len(human), "agreement": round((tp + tn) / len(human), 4) if human else None,
            "kappa": cohen_kappa(human, judge), "positive": positive,
            "confusion": {"both_pos": tp, "judge_only": fp, "human_only": fn, "both_neg": tn},
            "judge_precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "judge_recall": round(tp / (tp + fn), 4) if tp + fn else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", type=Path, default=LABELS)
    ap.add_argument("--judgments", type=Path, default=None, help="defaults to the sample's source run")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--sample", type=Path, default=SAMPLE)
    args = ap.parse_args()

    sample = json.loads(args.sample.read_text())
    jpath = args.judgments or ROOT / "runs" / sample["source_run"] / "judgments.jsonl"
    judg = {json.loads(l)["id"]: json.loads(l) for l in jpath.open()}
    labels = {json.loads(l)["item"]: json.loads(l) for l in args.labels.open() if l.strip()}

    kp_h, kp_j, cl_h, cl_j, decomp_err, cl_total = [], [], [], [], 0, 0
    tmp_h, tmp_j, con_h, con_j, incomplete, disagreements = [], [], [], [], [], []
    for it in sample["items"]:
        lab, j = labels.get(it["id"]), judg.get(it["id"])
        if lab is None or j is None:
            incomplete.append(it["id"])
            continue
        jkp = [k["asserted"] for k in j["grade"]["key_points"]]
        for i, h in enumerate(lab.get("kp", [])):
            if h is None or i >= len(jkp):
                continue
            kp_h.append(bool(h)); kp_j.append(jkp[i])
            if bool(h) != jkp[i]:
                disagreements.append({"id": it["id"], "type": "key_point", "index": i + 1, "human": h, "judge": jkp[i],
                                      "text": it["key_points"][i]})
        # Claims are aligned by index with the frozen sample (the judge's own decomposition).
        jcl = [c.get("supported") for c in j["grounding"]["claims"]]
        if [c["claim"] for c in j["grounding"]["claims"]] != it["claims"]:
            incomplete.append(f"{it['id']}(claims changed)")
            continue
        for i, h in enumerate(lab.get("claims", [])):
            if h is None:
                continue
            cl_total += 1
            if h == "x":
                decomp_err += 1
                continue
            human_unsup, judge_unsup = h == "n", not jcl[i]
            cl_h.append(human_unsup); cl_j.append(judge_unsup)
            if human_unsup != judge_unsup:
                disagreements.append({"id": it["id"], "type": "claim", "index": i + 1, "human": h,
                                      "judge": "y" if jcl[i] else "n", "text": it["claims"][i]})
        if it.get("ask_temporal") and lab.get("temporal") is not None and "temporal_error" in j["grade"]:
            tmp_h.append(bool(lab["temporal"])); tmp_j.append(bool(j["grade"]["temporal_error"]))
        if it.get("ask_conclusion") and lab.get("conclusion") is not None and "asserts_conclusion" in j["grade"]:
            con_h.append(bool(lab["conclusion"])); con_j.append(bool(j["grade"]["asserts_conclusion"]))

    kp = binary_report(kp_h, kp_j, "asserted")
    cl = binary_report(cl_h, cl_j, "unsupported")
    out = {
        "sample": str(args.sample), "judgments": str(jpath),
        "labels": str(args.labels.resolve().relative_to(ROOT)) if args.labels.resolve().is_relative_to(ROOT) else str(args.labels),
        "judge_version": sample["judge_version"], "labeled_items": len(sample["items"]) - len(incomplete),
        "incomplete": incomplete, "key_points": kp, "claims": cl,
        "claim_decomposition_error_rate": round(decomp_err / cl_total, 4) if cl_total else None,
        "temporal": binary_report(tmp_h, tmp_j, "temporal_error") if tmp_h else None,
        "conclusion": binary_report(con_h, con_j, "asserts_conclusion") if con_h else None,
        "adopt": {"rule": f"kappa >= {KAPPA_MIN}",
                  "key_points": kp["kappa"] is not None and kp["kappa"] >= KAPPA_MIN,
                  "claims": cl["kappa"] is not None and cl["kappa"] >= KAPPA_MIN},
        "disagreements": disagreements,
    }
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    for name in ("key_points", "claims", "temporal", "conclusion"):
        r = out[name]
        if r:
            print(f"{name:<11} n={r['n']:<4} agree={r['agreement']}  κ={r['kappa']}  "
                  f"judge P/R({r['positive']})={r['judge_precision']}/{r['judge_recall']}")
    print(f"claim decomposition errors: {out['claim_decomposition_error_rate']}")
    print(f"adopt (κ≥{KAPPA_MIN}): key_points={out['adopt']['key_points']} claims={out['adopt']['claims']}")
    print(f"incomplete: {incomplete}\n→ {args.out}")


if __name__ == "__main__":
    main()
