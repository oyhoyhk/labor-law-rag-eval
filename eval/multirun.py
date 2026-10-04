"""Compare configurations measured over several runs each: per-item mean over runs, paired bootstrap of the difference.

Usage: uv run python -m eval.multirun BASE_GLOB EXP_GLOB [EXP_GLOB ...] [--out PATH]
  each GLOB names the run directories of one configuration, e.g. 'runs/*_ab-checklist-r[123]'
Significant = 95% CI of ΔM0 excludes 0 and |Δ| > noise floor (eval/results/noise_floor_final.json M0 range).
"""

import argparse
import glob
import json
import random
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"M0": "m0_correct", "complete": "m4_complete", "recall_all": "m1_recall_all", "mrr": "m1_rr",
          "kp_coverage": "m4_kp_coverage", "cit_precision": "m3_citation_precision", "cit_recall": "m3_citation_recall",
          "unsupported": "m5_unsupported_rate"}
NOISE_M0 = 0.030


def load(pattern: str) -> list[dict]:
    dirs = sorted(d for d in glob.glob(str(ROOT / pattern)) if (Path(d) / "scores.jsonl").exists())
    return [{s["id"]: s for s in map(json.loads, (Path(d) / "scores.jsonl").open())} for d in dirs]


def per_item(runs: list[dict], field: str) -> dict[str, float]:
    out = {}
    for i in runs[0]:
        vals = [r[i].get(field) for r in runs if i in r and r[i].get(field) is not None]
        if len(vals) == len(runs):
            out[i] = mean(float(v) for v in vals)
    return out


def ci(d: list[float], seed: int = 0, n: int = 5000) -> tuple[float, float]:
    rng = random.Random(seed)
    bs = sorted(mean(rng.choice(d) for _ in d) for _ in range(n))
    return bs[int(n * 0.025)], bs[int(n * 0.975) - 1]


def compare(base: list[dict], exp: list[dict]) -> dict:
    out = {"runs": len(exp), "M0_runs": [round(mean(float(s["m0_correct"]) for s in r.values()), 3) for r in exp]}
    for name, f in FIELDS.items():
        a, b = per_item(base, f), per_item(exp, f)
        ids = [i for i in a if i in b]
        if not ids:
            continue
        d = [b[i] - a[i] for i in ids]
        lo, hi = ci(d)
        out[name] = {"n": len(ids), "base": round(mean(a[i] for i in ids), 3), "exp": round(mean(b[i] for i in ids), 3),
                     "delta": round(mean(d), 3), "ci": [round(lo, 3), round(hi, 3)]}
    for split in ("dev", "test"):
        a, b = per_item(base, "m0_correct"), per_item(exp, "m0_correct")
        ids = [i for i in a if i in b and base[0][i].get("split") == split]
        d = [b[i] - a[i] for i in ids]
        out[f"M0_{split}"] = {"n": len(ids), "delta": round(mean(d), 3), "ci": [round(x, 3) for x in ci(d)]}
    a, b = per_item(base, "m0_correct"), per_item(exp, "m0_correct")
    out["gained"] = sorted(i for i in a if i in b and b[i] - a[i] >= 0.5)
    out["lost"] = sorted(i for i in a if i in b and a[i] - b[i] >= 0.5)
    oos = lambda runs: mean(float(s["m2_correct_status"]) for r in runs for s in r.values() if s["level"] == "OOS")
    over = lambda runs: mean(float(s["status"] != "answered") for r in runs for s in r.values() if s["expected"] == "answered")
    out["oos_refusal"] = [round(oos(base), 3), round(oos(exp), 3)]
    out["over_refusal"] = [round(over(base), 3), round(over(exp), 3)]
    m0 = out["M0"]
    out["significant"] = m0["ci"][0] > 0 and m0["delta"] > NOISE_M0
    out["significant_worse"] = m0["ci"][1] < 0 and m0["delta"] < -NOISE_M0
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("exps", nargs="+")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    base = load(args.base)
    res = {"base": {"pattern": args.base, "runs": len(base)}}
    for e in args.exps:
        exp = load(e)
        if not exp:
            print(f"{e}: no runs")
            continue
        r = res[e] = compare(base, exp)
        m = r["M0"]
        print(f"{e:42s} runs={r['runs']} M0 {m['base']:.3f}→{m['exp']:.3f} Δ{m['delta']:+.3f} CI[{m['ci'][0]:+.3f},{m['ci'][1]:+.3f}]"
              f" {'SIGNIFICANT' if r['significant'] else 'worse' if r['significant_worse'] else 'n.s.'}"
              f" | dev {r['M0_dev']['delta']:+.3f} test {r['M0_test']['delta']:+.3f} | +{r['gained']} -{r['lost']}")
    if args.out:
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
