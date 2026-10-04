"""Blind human review of the key-point verdicts all three judges (Luna / Opus / Codex) agreed on.

One card per (item, key point) whose verdicts agreed in every run; the answer shown is one run picked at random.
Opus/Codex verdicts, quotes and reasons are shown on every card (reviewer's choice), so decisions are non-blind and
stored with revealed_before=true. Order is shuffled; the
agreed verdicts are also kept in tools/kp_blind_key.json. Decisions go to the artifact db collection kp_blind_v1.

Usage: uv run python tools/build_kp_blind_page.py eval/results/rejudge_qwen3-4B-k10-official.json
Output: tools/kp_blind_page.html, tools/kp_blind_key.json
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).parent


def main() -> None:
    d = json.loads(Path(sys.argv[1]).read_text())
    gold = {g["id"]: g for g in map(json.loads, (ROOT / "eval/gold/gold_v2.jsonl").open())}
    by_pair: dict[tuple, list] = {}
    disputed = set()
    for a in d["answers"]:
        if a.get("expected", "answered") != "answered":
            continue
        for k, (lu, op, cx) in enumerate(zip(a["luna"], a["opus"], a["codex"])):
            if lu is None or op is None or cx is None:
                continue
            if lu["ok"] == op["ok"] == cx["ok"]:
                by_pair.setdefault((a["id"], k), []).append((a, op["ok"]))
            else:
                disputed.add((a["id"], k))
    rng = random.Random(0)
    cards, key = [], {}
    for (i, k), runs in sorted(by_pair.items()):
        if (i, k) in disputed:  # already reviewed in kp_review_v1
            continue
        a, verdict = rng.choice(runs)
        ck = f"{i}-kp{k + 1}"
        judges = {j: {f: a[j][k].get(f, "") for f in ("ok", "quote", "reason")} for j in ("opus", "codex")}
        cards.append({"key": ck, "id": i, "level": gold[i]["level"], "question": gold[i]["question"], "kp_index": k + 1,
                      "all_kps": gold[i]["key_points"], "answer": a["answer"], "reference": gold[i]["reference_answer"], "judges": judges})
        key[ck] = {"run": a["run"], "judges_agree": verdict}
    rng.shuffle(cards)
    data = json.dumps({"items": cards}, ensure_ascii=False).replace("</", "<\\/")
    (HERE / "kp_blind_page.html").write_text((HERE / "kp_blind_template.html").read_text().replace("/*__DATA__*/null", data))
    (HERE / "kp_blind_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1))
    print(len(cards), "cards")


if __name__ == "__main__":
    main()
