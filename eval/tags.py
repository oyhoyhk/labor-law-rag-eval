"""Structural tags for gold items, derived from the corpus graph and chunk layout (never from system outputs).

  exception   two evidence articles where one overrides the other ("…에도 불구하고")  → reverse-ref experiment
  split       key-point literals sit in 2+ chunks of one evidence article             → sibling-chunk experiment
  temporal    an evidence article is not plainly in force on as_of                    → status injection (H4)
  delegation  evidence holds a law article together with its implementing decree      → link expansion / k
"""

import json
import re
from collections import defaultdict
from functools import cache
from pathlib import Path

from app.ingest.provision import status_at

ROOT = Path(__file__).resolve().parents[1]
TAGS = ["exception", "split", "temporal", "delegation"]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


@cache
def _graph() -> dict:
    return json.loads((ROOT / "data/processed/provision_graph.json").read_text())["nodes"]


@cache
def _chunks() -> dict:
    out = defaultdict(dict)
    for l in (ROOT / "data/index/article/chunks.jsonl").open():
        c = json.loads(l)
        for a in c["article_ids"]:
            out[a][c["chunk_id"]] = _norm(c["text"])
    return out


def item_tags(item: dict) -> list[str]:
    g, ch, ev, tags = _graph(), _chunks(), item["gold_evidence"], set()
    for a in ev:
        node = g.get(a, {})
        if any(node.get("referenced_by_cues", {}).get(b) == "exception" for b in ev):
            tags.add("exception")
        if any(i in ev for i in node.get("implementing_provisions", [])):
            tags.add("delegation")
        if node and status_at(node, item["as_of"])["status"] != "in_force":
            tags.add("temporal")
        if len(ch.get(a, {})) >= 2:
            hit = {cid for alts in item.get("key_point_literals", []) for cid, txt in ch[a].items()
                   if any(_norm(x) in txt for x in alts)}
            if len(hit) >= 2:
                tags.add("split")
    return [t for t in TAGS if t in tags]
