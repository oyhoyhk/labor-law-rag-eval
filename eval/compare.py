"""Compare evaluation runs.

  noise RUN RUN [RUN...]   identical-config repeats → per-metric spread (the noise floor)
  diff BASE EXP            metric deltas, judged against the noise floor and a paired bootstrap CI,
                           overall, per structural tag (eval/tags.py) and per split (split:dev, split:test)
  --noise PATH             noise-floor file written by `noise` / read by `diff` (default eval/results/noise_floor.json)

Usage:
  uv run python -m eval.compare noise runs/a runs/b runs/c
  uv run python -m eval.compare diff runs/baseline runs/h4-off
"""

import argparse
import json
import random
from pathlib import Path
from statistics import mean, pstdev

from eval.metrics import aggregate
from eval.tags import TAGS, item_tags

ROOT = Path(__file__).resolve().parents[1]
NOISE = ROOT / "eval" / "results" / "noise_floor.json"
METRICS = ["M1_recall_any", "M1_recall_all", "M1_mrr", "M2_oos_refusal", "M2_l5b_no_assertion", "M2_over_refusal",
           "M3_citation_precision", "M3_citation_recall", "M4_kp_coverage", "M4_all_kp", "M4_complete",
           "M5_unsupported_rate", "M6_temporal_error"]
# Per-item score field behind each metric, for the paired bootstrap (None = not item-pairable).
ITEM_FIELD = {"M1_recall_any": "m1_recall_any", "M1_recall_all": "m1_recall_all", "M1_mrr": "m1_rr",
              "M3_citation_precision": "m3_citation_precision", "M3_citation_recall": "m3_citation_recall",
              "M4_kp_coverage": "m4_kp_coverage", "M4_all_kp": "m4_all_kp", "M4_complete": "m4_complete",
              "M5_unsupported_rate": "m5_unsupported_rate", "M6_temporal_error": "m6_temporal_error"}
LOWER_IS_BETTER = {"M2_over_refusal", "M5_unsupported_rate", "M6_temporal_error"}
GOLD = ROOT / "eval" / "gold" / "gold_v2.jsonl"
SPLITS = ROOT / "eval" / "gold" / "splits.json"
# Per-tag subset metrics. `complete` = answerable item answered with every key point (refusal counts as a miss).
SUBSET_FIELDS = ["complete", "m4_kp_coverage", "m1_recall_all"]


def scores(run: Path) -> list[dict]:
    return [json.loads(l) for l in (run / "scores.jsonl").open()]


def tag_ids() -> dict[str, set[str]]:
    gold = [json.loads(l) for l in GOLD.open() if l.strip()]
    tagged = {g["id"]: item_tags(g) for g in gold}
    return {t: {i for i, ts in tagged.items() if t in ts} for t in TAGS}


def split_ids() -> dict[str, set[str]]:
    splits = json.loads(SPLITS.read_text())
    return {f"split:{s}": {i for i, v in splits.items() if v == s} for s in ("dev", "test")}


def subset_ids() -> dict[str, set[str]]:
    return tag_ids() | split_ids()


def subset_value(rows: list[dict], ids: set[str], field: str):
    vals = [subset_field(r, field) for r in rows if r["id"] in ids]
    vals = [float(v) for v in vals if v is not None]
    return (round(mean(vals), 4), len(vals)) if vals else (None, 0)


def subset_field(r: dict, field: str):
    if field == "complete":  # recomputed so older scores.jsonl without m4_complete still compare
        return (r["status"] == "answered" and r.get("m4_all_kp") is True) if r["expected"] == "answered" else None
    return r.get(field)


def overall(run: Path) -> dict:
    return {k: v[0] for k, v in aggregate(scores(run)).items() if k in METRICS}


def cmd_noise(runs: list[Path], path: Path = NOISE) -> None:
    per = [overall(r) for r in runs]
    out = {"runs": [str(r.relative_to(ROOT)) for r in runs], "metrics": {}}
    for k in METRICS:
        vals = [p[k] for p in per if p[k] is not None]
        if vals:
            out["metrics"][k] = {"values": vals, "mean": round(mean(vals), 4), "min": min(vals), "max": max(vals),
                                 "range": round(max(vals) - min(vals), 4), "std": round(pstdev(vals), 4)}
    out["subsets"] = {}
    for t, ids in subset_ids().items():
        for f in SUBSET_FIELDS:
            vals = [subset_value(scores(r), ids, f)[0] for r in runs]
            vals = [v for v in vals if v is not None]
            if vals:
                out["subsets"][f"{t}:{f}"] = {"values": vals, "range": round(max(vals) - min(vals), 4)}
    # Items whose outcome changed between repeats (status or retrieval or key-point coverage).
    s = [{x["id"]: x for x in scores(r)} for r in runs]
    unstable = []
    for i in s[0]:
        sigs = {(x[i]["status"], x[i].get("m4_kp_coverage"), x[i].get("m1_recall_any")) for x in s}
        if len(sigs) > 1:
            unstable.append(i)
    out["unstable_items"] = unstable
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{'metric':<24}{'values':<30}{'range':>8}")
    for k, m in out["metrics"].items():
        print(f"{k:<24}{' / '.join(f'{v:.3f}' for v in m['values']):<30}{m['range']:>8.3f}")
    print(f"unstable items ({len(unstable)}): {unstable}\n→ {path}")


def bootstrap_ci(a: list[dict], b: list[dict], field: str, n: int = 2000, seed: int = 0, ids: set | None = None):
    by_a = {x["id"]: subset_field(x, field) for x in a if ids is None or x["id"] in ids}
    by_b = {x["id"]: subset_field(x, field) for x in b}
    pairs = [(float(by_a[i]), float(by_b[i])) for i in by_a if by_a[i] is not None and by_b.get(i) is not None]
    if len(pairs) < 5:
        return None
    rng, deltas = random.Random(seed), []
    for _ in range(n):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        deltas.append(mean(y for _, y in sample) - mean(x for x, _ in sample))
    deltas.sort()
    return round(deltas[int(0.025 * n)], 4), round(deltas[int(0.975 * n)], 4), len(pairs)


def cmd_diff(base: Path, exp: Path, path: Path = NOISE) -> None:
    noise = json.loads(path.read_text())["metrics"] if path.exists() else {}
    a, b = overall(base), overall(exp)
    sa, sb = scores(base), scores(exp)
    print(f"base {base.name}\nexp  {exp.name}\n")
    print(f"{'metric':<24}{'base':>8}{'exp':>8}{'Δ':>8}{'noise':>8}  {'95% CI (paired)':<20} verdict")
    rows = []
    for k in METRICS:
        if a[k] is None or b[k] is None:
            continue
        d = b[k] - a[k]
        band = noise.get(k, {}).get("range")
        ci = bootstrap_ci(sa, sb, ITEM_FIELD[k]) if k in ITEM_FIELD else None
        beyond_noise = band is not None and abs(d) > band
        ci_excludes_0 = ci is not None and (ci[0] > 0 or ci[1] < 0)
        better = (d < 0) if k in LOWER_IS_BETTER else (d > 0)
        verdict = ("개선" if better else "악화") if (beyond_noise and (ci is None or ci_excludes_0)) and d else "유의하지 않음"
        rows.append({"metric": k, "base": a[k], "exp": b[k], "delta": round(d, 4), "noise_range": band,
                     "ci95": ci, "verdict": verdict})
        print(f"{k:<24}{a[k]:>8.3f}{b[k]:>8.3f}{d:>+8.3f}{'—' if band is None else f'{band:.3f}':>8}  "
              f"{'—' if ci is None else f'[{ci[0]:+.3f}, {ci[1]:+.3f}] n={ci[2]}':<20} {verdict}")
    noise_sub = json.loads(path.read_text()).get("subsets", {}) if path.exists() else {}
    subsets = []
    print(f"\n{'tag:field':<28}{'n':>4}{'base':>8}{'exp':>8}{'Δ':>8}{'noise':>8}  {'95% CI (paired)':<20} verdict")
    for t, ids in subset_ids().items():
        for f in SUBSET_FIELDS:
            (va, n), (vb, _) = subset_value(sa, ids, f), subset_value(sb, ids, f)
            if va is None or vb is None:
                continue
            d, band = round(vb - va, 4), noise_sub.get(f"{t}:{f}", {}).get("range")
            ci = bootstrap_ci(sa, sb, f, ids=ids)
            sig = band is not None and abs(d) > band and ci is not None and (ci[0] > 0 or ci[1] < 0)
            verdict = ("개선" if d > 0 else "악화") if sig and d else "유의하지 않음"
            subsets.append({"tag": t, "field": f, "n": n, "base": va, "exp": vb, "delta": d, "noise_range": band,
                            "ci95": ci, "verdict": verdict})
            print(f"{t + ':' + f:<28}{n:>4}{va:>8.3f}{vb:>8.3f}{d:>+8.3f}{'—' if band is None else f'{band:.3f}':>8}  "
                  f"{'—' if ci is None else f'[{ci[0]:+.3f}, {ci[1]:+.3f}]':<20} {verdict}")
    out = exp / "diff_vs_base.json"
    rel = lambda p: str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name
    out.write_text(json.dumps({"base": rel(base), "exp": rel(exp), "rows": rows, "subsets": subsets},
                              ensure_ascii=False, indent=1))
    print(f"\n→ {out.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("noise")
    n.add_argument("runs", nargs="+", type=Path)
    d = sub.add_parser("diff")
    d.add_argument("base", type=Path)
    d.add_argument("exp", type=Path)
    for p in (n, d):
        p.add_argument("--noise", type=Path, default=NOISE, help="noise-floor JSON (output of noise, input of diff)")
    args = ap.parse_args()
    if args.cmd == "noise":
        cmd_noise([r.resolve() for r in args.runs], args.noise.resolve())
    else:
        cmd_diff(args.base.resolve(), args.exp.resolve(), args.noise.resolve())


if __name__ == "__main__":
    main()
