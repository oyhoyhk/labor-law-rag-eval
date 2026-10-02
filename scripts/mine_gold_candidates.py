"""Mine gold-set v2 candidates from corpus structure alone (no system outputs are read).

Candidates are drawn by type so each Part C experiment has a target subset:
  exception  article A is overridden by article B ("A에도 불구하고") → reverse-ref experiment
  split      article indexed as 2+ chunks                            → sibling-chunk experiment
  temporal   article with a scheduled change or a sunset on AS_OF    → H4 (status injection)
  delegation law article whose detail lives in a decree/rule         → link expansion / k

Articles already used as evidence in gold v1.1 are excluded. Output: eval/gold/candidates_v2.json

Usage: uv run python scripts/mine_gold_candidates.py
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.ingest.provision import status_at  # noqa: E402

AS_OF = "2026-10-01"
SEED = 7
PER_TYPE = 20  # oversample; drafting keeps the ones that make a checkable question

graph = json.loads((ROOT / "data/processed/provision_graph.json").read_text())["nodes"]
gold = [json.loads(l) for l in (ROOT / "eval/gold/gold_v1_1.jsonl").open()]
used = {e for g in gold for e in g["gold_evidence"]}
chunks = defaultdict(list)
for l in (ROOT / "data/index/article/chunks.jsonl").open():
    c = json.loads(l)
    for a in c["article_ids"]:
        chunks[a].append(c["chunk_id"])


def is_law(aid: str) -> bool:
    return not aid.split("#")[0].endswith(("시행령", "시행규칙"))


def fresh(*aids: str) -> bool:
    return all(a in graph and graph[a]["in_current"] and a not in used for a in aids)


cands = {"exception": [], "split": [], "temporal": [], "delegation": []}
for aid, n in sorted(graph.items()):
    for src, cue in n.get("referenced_by_cues", {}).items():
        if cue == "exception" and fresh(aid, src):
            cands["exception"].append({"target": aid, "overridden_by": src})
    if len(set(chunks.get(aid, []))) >= 2 and fresh(aid):
        cands["split"].append({"article": aid, "chunks": sorted(set(chunks[aid]))})
    st = status_at(n, AS_OF)
    if st["status"] != "in_force" and aid not in used:
        cands["temporal"].append({"article": aid, "status": st["status"], "notes": st["notes"]})
    if is_law(aid) and fresh(aid) and n["implementing_provisions"]:
        impl = [i for i in n["implementing_provisions"] if fresh(i)]
        if impl:
            cands["delegation"].append({"article": aid, "implementing": impl})

rng = random.Random(SEED)
out = {"as_of": AS_OF, "seed": SEED, "excluded_v1_1_evidence": len(used),
       "pool_sizes": {k: len(v) for k, v in cands.items()},
       "candidates": {k: rng.sample(v, min(PER_TYPE, len(v))) for k, v in cands.items()}}
path = ROOT / "eval/gold/candidates_v2.json"
path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(out["pool_sizes"], "→", path.relative_to(ROOT))
