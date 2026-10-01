"""Judge consistency: grade the same answers several times and count verdict flips.

Usage: uv run python -m eval.judge_consistency runs/<a> runs/<b> [runs/<c> ...]
All runs must share the same predictions (same cached answers); only the judge differs.
"""

import json
import sys
from itertools import combinations
from pathlib import Path


def load(run: Path) -> tuple[dict, dict]:
    preds = {json.loads(l)["id"]: json.loads(l) for l in (run / "predictions.jsonl").open()}
    judg = {json.loads(l)["id"]: json.loads(l) for l in (run / "judgments.jsonl").open()}
    return preds, judg


def main(paths: list[str]) -> dict:
    runs = [load(Path(p)) for p in paths]
    base_preds = runs[0][0]
    for preds, _ in runs[1:]:
        same = all(preds[i].get("answer") == base_preds[i].get("answer") for i in base_preds)
        assert same, "runs differ in generated answers — not a judge-only comparison"
    ids = sorted(set.intersection(*(set(j) for _, j in runs)))
    kp_total = kp_flips = items_kp_flip = 0
    temporal_flips = concl_flips = 0
    unsup_rates, claim_counts, flipped_items = [], [], []
    for i in ids:
        js = [j[i] for _, j in runs]
        vecs = [[k["asserted"] for k in j["grade"]["key_points"]] for j in js]
        n = len(vecs[0])
        flips = sum(any(v[k] != vecs[0][k] for v in vecs[1:]) for k in range(n))
        kp_total, kp_flips = kp_total + n, kp_flips + flips
        items_kp_flip += bool(flips)
        if len({j["grade"].get("temporal_error") for j in js}) > 1:
            temporal_flips += 1
        if len({j["grade"].get("asserts_conclusion") for j in js}) > 1:
            concl_flips += 1
        rates = [j["grounding"]["n_unsupported"] / j["grounding"]["n_claims"] if j["grounding"]["n_claims"] else 0
                 for j in js]
        unsup_rates.append(max(rates) - min(rates))
        claim_counts.append(max(j["grounding"]["n_claims"] for j in js) - min(j["grounding"]["n_claims"] for j in js))
        if flips or unsup_rates[-1] > 0:
            flipped_items.append({"id": i, "kp_flips": flips, "unsup_rates": [round(r, 3) for r in rates],
                                  "n_claims": [j["grounding"]["n_claims"] for j in js]})
    agg = lambda run: sum((j["grounding"]["n_unsupported"] / j["grounding"]["n_claims"]) if j["grounding"]["n_claims"] else 0
                          for j in run.values()) / len(run)  # noqa: E731
    out = {
        "runs": paths, "items": len(ids), "key_points": kp_total,
        "kp_flip_rate": round(kp_flips / kp_total, 4) if kp_total else None,
        "items_with_kp_flip": items_kp_flip, "temporal_flips": temporal_flips, "conclusion_flips": concl_flips,
        "unsupported_rate_item_range_mean": round(sum(unsup_rates) / len(ids), 4),
        "items_with_unsupported_change": sum(r > 0 for r in unsup_rates),
        "claim_count_range_mean": round(sum(claim_counts) / len(ids), 2),
        "M5_by_run": [round(agg(j), 4) for _, j in runs],
        "pairwise_kp_agreement": [
            round(sum(a[i]["grade"]["key_points"][k]["asserted"] == b[i]["grade"]["key_points"][k]["asserted"]
                      for i in ids for k in range(len(a[i]["grade"]["key_points"]))) / kp_total, 4)
            for (_, a), (_, b) in combinations(runs, 2)],
        "changed_items": flipped_items,
    }
    print(json.dumps({k: v for k, v in out.items() if k != "changed_items"}, ensure_ascii=False, indent=1))
    print(f"changed items: {[c['id'] for c in flipped_items]}")
    return out


if __name__ == "__main__":
    result = main(sys.argv[1:])
    Path("eval/results/judge_consistency.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
