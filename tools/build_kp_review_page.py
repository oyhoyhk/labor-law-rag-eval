"""Human review of key points the three judges (Luna / Opus / Codex) disagree on.

One card per (item, key point) with a disagreement in any run; the reviewer decides whether the answer contains the
key point, or whether the key point itself asks for too much (a gold-set decision). Decisions go to the artifact
db collection kp_review_v1 and are read back with ArtifactData.

Usage: uv run python tools/build_kp_review_page.py eval/results/rejudge_qwen3-4B-k10-all.json
Output: tools/kp_review_page.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).with_name("kp_review_template.html")
# Context the reviewer needs that the judges did not see (found while analysing these items).
NOTES = {
    ("g031", 0): "질문의 핵심(지금 바로 되나 → 아니오, 2027.6.10부터)은 답변에 있음. 이 포인트는 공포일(2026.6.9)·신설·대통령령 위임까지 묶어 요구함 → 포인트를 완화할지 결정 필요",
    ("l5b01", 2): "실제로 들어간 판례는 2018다296472(2025.1.23, 같은 법리를 적용한 후속 판례)로 적용 시점 설명이 없음. 결론('올해 수당에 포함')은 적용 시점 없이도 같음 → 이 포인트를 필수로 둘지, 후속 판례도 정답 판례로 인정할지 결정 필요",
}


def main() -> None:
    src = Path(sys.argv[1])
    d = json.loads(src.read_text())
    gold = {g["id"]: g for g in map(json.loads, (ROOT / "eval/gold/gold_v2.jsonl").open())}
    cards: dict[tuple, dict] = {}
    for a in d["answers"]:
        for k, (lu, op, cx) in enumerate(zip(a["luna"], a["opus"], a["codex"])):
            if lu["ok"] == op["ok"] == cx["ok"]:
                continue
            key = (a["id"], k)
            c = cards.setdefault(key, {"key": f"{a['id']}-kp{k + 1}", "id": a["id"], "level": gold[a["id"]]["level"],
                                       "question": gold[a["id"]]["question"], "kp_index": k + 1, "kp": a["key_points"][k],
                                       "all_kps": a["key_points"], "reference": gold[a["id"]]["reference_answer"],
                                       "note": NOTES.get(key, ""), "answers": []})
            c["answers"].append({"run": a["run"].split("_", 1)[1], "answer": a["answer"],
                                 "luna": lu, "opus": op, "codex": cx})
    for c in cards.values():
        v = c["answers"][0]
        c["pattern"] = ("luna_only_yes" if v["luna"]["ok"] and not v["opus"]["ok"] and not v["codex"]["ok"]
                        else "codex_only_no" if v["luna"]["ok"] and v["opus"]["ok"] and not v["codex"]["ok"]
                        else "luna_only_no" if not v["luna"]["ok"] and v["opus"]["ok"] and v["codex"]["ok"] else "mixed")
    order = {"luna_only_yes": 0, "codex_only_no": 1, "luna_only_no": 2, "mixed": 3}
    items = sorted(cards.values(), key=lambda c: (order[c["pattern"]], c["id"], c["kp_index"]))
    data = json.dumps({"source": src.name, "runs": d["runs"], "items": items}, ensure_ascii=False).replace("</", "<\\/")
    out = Path(__file__).with_name("kp_review_page.html")
    out.write_text(TEMPLATE.read_text().replace("/*__DATA__*/null", data))
    print(out, len(items), "cards")


if __name__ == "__main__":
    main()
