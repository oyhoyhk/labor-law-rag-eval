"""Minimum detectable effect per structural tag, from identical-config repeat runs.

An experiment's change on a subset can be called real only if it beats both the repeat-to-repeat range and the
half-width of a paired bootstrap CI between two identical runs (the null spread). MDE = max of the two.
Comparing MDE across gold-set versions shows whether a larger gold set can detect smaller effects.

Usage: uv run python -m eval.mde --gold eval/gold/gold_v1.jsonl runs/a runs/b runs/c
"""

import argparse
import json
from itertools import combinations
from pathlib import Path

from eval.compare import bootstrap_ci, scores, subset_value
from eval.tags import TAGS, item_tags

FIELD = "complete"


def mde(runs: list[Path], gold: Path) -> dict:
    items = [json.loads(l) for l in gold.open() if l.strip()]
    groups = {"all": {i["id"] for i in items}} | {t: {i["id"] for i in items if t in item_tags(i)} for t in TAGS}
    per_run = [scores(r) for r in runs]
    out = {}
    for name, ids in groups.items():
        vals = [subset_value(s, ids, FIELD) for s in per_run]
        n = vals[0][1]
        if n < 5:  # paired bootstrap needs a handful of pairs; below that no change can be judged
            out[name] = {"n": n, "range": None, "null_ci_halfwidth": None, "mde": None}
            continue
        rng = max(v for v, _ in vals) - min(v for v, _ in vals)
        halves = []
        for a, b in combinations(per_run, 2):
            ci = bootstrap_ci(a, b, FIELD, ids=ids)
            if ci:
                halves.append((ci[1] - ci[0]) / 2)
        half = sum(halves) / len(halves)
        out[name] = {"n": n, "range": round(rng, 4), "null_ci_halfwidth": round(half, 4),
                     "mde": round(max(rng, half), 4), "mde_items": round(max(rng, half) * n, 1)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("runs", nargs="+", type=Path)
    a = ap.parse_args()
    res = mde([r.resolve() for r in a.runs], a.gold.resolve())
    print(f"{'subset':<12}{'n':>4}{'range':>8}{'null CI ±':>11}{'MDE':>8}{'≈items':>8}")
    for k, v in res.items():
        f = lambda x: "—" if x is None else f"{x:.3f}"
        print(f"{k:<12}{v['n']:>4}{f(v['range']):>8}{f(v['null_ci_halfwidth']):>11}{f(v['mde']):>8}"
              f"{'—' if v['mde'] is None else v['mde_items']:>8}")
    if a.out:
        a.out.write_text(json.dumps({"gold": str(a.gold), "runs": [r.name for r in a.runs], "field": FIELD,
                                     "subsets": res}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
