"""Second, cross-family judge: Claude Opus via the `claude -p` CLI on the frozen labeling sample.

It sees exactly what the human rater sees (question, key points, answer, the model's context, and
the Luna judge's claim list) and never the Luna verdicts. Claims are verified, not re-decomposed,
so verdicts align one-to-one with the Luna judge and the human labels.

Output uses the human-label format with rater="claude-opus", so `eval.calibrate --labels` works on it.
Usage: uv run python -m eval.cross_judge [--ids g013,l5a01] [--workers 3]
"""

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from app.rag import graph
from app.ingest.provision import status_at

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "eval" / "gold" / "human_label_sample_v1.json"
OUT = ROOT / "eval" / "gold" / "opus_labels_v1.jsonl"
META = ROOT / "eval" / "results" / "cross_judge_opus_meta.json"
CROSS_VERSION = "cross-judge-v1"

SYSTEM = ("You are a strict grader of a Korean labor-law QA system. Use only the given criteria, answer, and "
          "evidence; never your own legal knowledge. Output exactly one JSON object and nothing else.")

PROMPT = """한국 노동법령 QA 시스템의 답변을 채점하세요. 자신의 법률 지식은 쓰지 말고 주어진 기준·답변·근거만 비교하세요.

[판정 규칙]
1. key_points: 답변이 그 사실을 명시적으로 단언하면 true. 표현이 달라도 의미(수치·기간·조건·주체·의무/재량)가 같으면 true. 다르거나 반대이거나 언급이 없거나 앞뒤가 모순되면 false.
2. claims: 각 주장(답변에서 미리 분해됨)에 대해
   - "y": [근거] 블록 문장이 직접 말하거나, 근거 문장과 질문의 사실만으로 반드시 도출되는 결론·계산
   - "n": 근거에 없거나 근거와 다르거나, 근거만으로 도출되지 않는 일반 지식
   - "x": 분해된 주장이 답변의 실제 의미와 다름(분해 오류)
   근거 블록에 적힌 시행 상태·날짜 정보도 근거로 인정합니다.
{extra_rules}
[질문]
{question}

[key_points]
{key_points}

[답변]
{answer}

[근거]
{context}

[claims]
{claims}

[출력 형식 — JSON 하나만]
{{"key_points": [{{"index": 1, "asserted": true}}], "claims": [{{"index": 1, "verdict": "y"}}]{extra_fields}}}"""

TEMPORAL_RULE = "3. temporal_error: 기준일 {as_of} 기준 아래 시점 사실과 달리, 시행 전이거나 효력을 잃은 내용을 지금 적용되는 것처럼 서술했으면 true.\n{facts}\n"
CONCLUSION_RULE = ("3. asserts_conclusion: 이 질문은 법령 조문만으로 결론을 낼 수 없습니다. 답변이 단정할 수 없다고 밝히지 않고 "
                   "결론(예/아니오 등)을 단정했으면 true, 관련 조문을 안내하며 결정적 기준이 조문에 없다고 밝혔으면 false.\n")


def build_prompt(it: dict, gold: dict) -> str:
    extra_rules, extra_fields = "", ""
    if it.get("ask_temporal"):
        facts = [f"- {aid}: {n}" for aid in gold["gold_evidence"] if aid in graph()
                 for n in status_at(graph()[aid], it["as_of"])["notes"]]
        extra_rules += TEMPORAL_RULE.format(as_of=it["as_of"], facts="\n".join(facts) or "- (없음)")
        extra_fields += ', "temporal_error": false'
    if it.get("ask_conclusion"):
        extra_rules += CONCLUSION_RULE
        extra_fields += ', "asserts_conclusion": false'
    kps = it["key_points"] if it["expected_status"] == "answered" else []
    return PROMPT.format(
        extra_rules=extra_rules, extra_fields=extra_fields, question=it["question"],
        key_points="\n".join(f"{i}. {k}" for i, k in enumerate(kps, 1)) or "(없음 — key_points는 빈 배열로)",
        answer=it["answer"], context="\n\n".join(c["text"] for c in it["context"]),
        claims="\n".join(f"{i}. {c}" for i, c in enumerate(it["claims"], 1)))


def parse_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def judge_one(it: dict, gold: dict) -> dict:
    prompt = build_prompt(it, gold)
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "json", "--system-prompt", SYSTEM,
           "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]
    for attempt in range(2):
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600,
                              cwd=ROOT.parent)  # outside the repo so no project CLAUDE.md is involved
        try:
            meta = json.loads(proc.stdout)
            out = parse_json(meta["result"])
            break
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            if attempt:
                raise RuntimeError(f"{it['id']}: unparseable Opus output: {proc.stdout[:300]} {proc.stderr[:300]}") from e
    kps = {int(k["index"]): bool(k["asserted"]) for k in out.get("key_points", [])}
    cls = {int(c["index"]): c["verdict"] for c in out.get("claims", [])}
    n_kp = len(it["key_points"]) if it["expected_status"] == "answered" else 0
    label = {"item": it["id"], "rater": "claude-opus",
             "kp": [kps.get(i) for i in range(1, n_kp + 1)],
             "claims": [cls.get(i) if cls.get(i) in ("y", "n", "x") else None for i in range(1, len(it["claims"]) + 1)],
             "at": datetime.now().isoformat(timespec="seconds")}
    if it.get("ask_temporal"):
        label["temporal"] = out.get("temporal_error")
    if it.get("ask_conclusion"):
        label["conclusion"] = out.get("asserts_conclusion")
    usage = meta.get("modelUsage", {})
    return {"label": label, "cost_usd": meta.get("total_cost_usd", 0), "models": list(usage)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    sample = json.loads(SAMPLE.read_text())
    gold = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval" / "gold" / "gold_v1.jsonl").open()}
    items = [i for i in sample["items"] if not args.ids or i["id"] in args.ids.split(",")]
    graph()  # load once before threads
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda it: judge_one(it, gold[it["id"]]), items))
    existing = {}
    if OUT.exists() and args.ids:
        existing = {json.loads(l)["item"]: json.loads(l) for l in OUT.open()}
    for r in results:
        existing[r["label"]["item"]] = r["label"]
    order = [i["id"] for i in sample["items"]]
    OUT.write_text("".join(json.dumps(existing[i], ensure_ascii=False) + "\n" for i in order if i in existing))
    meta = {"cross_version": CROSS_VERSION, "models": sorted({m for r in results for m in r["models"]}),
            "cli": subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip(),
            "items": len(results), "cost_usd": round(sum(r["cost_usd"] for r in results), 4),
            "missing_verdicts": [r["label"]["item"] for r in results
                                 if None in r["label"]["kp"] or None in r["label"]["claims"]],
            "run_at": datetime.now().isoformat(timespec="seconds")}
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
