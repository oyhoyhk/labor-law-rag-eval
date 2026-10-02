"""Recompute scores and reports of saved runs with the current metric definitions (no LLM calls).

Usage: uv run python -m eval.rescore runs/<run> [eval/results/baseline ...]
"""

import json
import sys
from pathlib import Path

from eval.metrics import aggregate, by_group, item_scores
from eval.run import GOLD, SPLITS, report_md


def rescore(run: Path) -> dict:
    gold = {json.loads(l)["id"]: json.loads(l) for l in GOLD.open()}
    splits = json.loads(SPLITS.read_text())
    preds = [json.loads(l) for l in (run / "predictions.jsonl").open()]
    judg = {json.loads(l)["id"]: json.loads(l) for l in (run / "judgments.jsonl").open() if l.strip()}
    scores = [item_scores(gold[p["id"]] | {"split": splits[p["id"]]}, p, judg.get(p["id"])) for p in preds]
    overall, levels, by_split = aggregate(scores), by_group(scores, "level"), by_group(scores, "split")
    (run / "scores.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in scores))
    (run / "report.json").write_text(json.dumps({"overall": overall, "by_level": levels, "by_split": by_split},
                                                ensure_ascii=False, indent=1))
    manifest = json.loads((run / "manifest.json").read_text())
    (run / "report.md").write_text(report_md(manifest["name"], overall, levels, by_split, scores, manifest))
    return overall


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        o = rescore(Path(arg))
        print(arg, {k: v[0] for k, v in o.items() if k.startswith("M2")})
