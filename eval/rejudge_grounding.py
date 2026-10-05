"""Re-grade Measure 5 (unsupported claims) and Measure 6 (temporal error) with Opus and Codex instead of Luna.

Measure 5 keeps the claim list the Luna judge already split each answer into (judgments.jsonl → grounding.claims),
so every judge rules on the same units; only the supported/unsupported verdict is re-done, against the same context
blocks the answer was generated from. Measure 6 is asked for Case4 (L4) items, with the effectivity facts of their
gold evidence, under the Luna judge's definition.

Official rule, as for Measure 0: a claim counts as supported only when Opus AND Codex both say supported, and a Case4
answer counts as free of temporal error only when both say so.
  Measure 5 = mean over answered items of (claims not supported by both) / (claims)
  Measure 6 = mean over answered Case4 items of (not error-free by both)

Usage: uv run python -m eval.rejudge_grounding NAME runs/a runs/b runs/c [--workers 6] [--max-calls N]
Output: eval/results/grounding_<NAME>.json; verdicts cached in eval/results/rejudge_cache/grounding_<NAME>.jsonl
"""

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from statistics import mean

from eval.rejudge import Cache, codex, opus
from eval.run import temporal_facts

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ("You are a strict grader of grounding in a Korean labor-law QA system. Use only the given context blocks, "
          "question, answer and facts; never your own legal knowledge. Output exactly one JSON object and nothing else.")
PROMPT = """한국 노동법령 QA 답변의 근거 충실성을 채점하세요. 자신의 법률 지식은 쓰지 말고 아래 자료만 비교하세요.

[판정 규칙]
1. 주장마다 supported를 판정한다.
   - true: [근거] 블록 문장이 직접 말하는 내용, 또는 근거 블록 문장과 질문의 사실만으로 반드시 도출되는 결론·계산. 근거 블록에 적힌 시행 상태·날짜 정보도 근거로 인정
   - false: 근거 블록에 없는 사실, 근거와 다른 내용, 근거만으로는 도출되지 않는 일반 지식
2. temporal_error: [시점 사실]이 있으면, 답변이 그 사실과 달리 아직 시행되지 않았거나 효력을 잃은 내용을 기준일 현재 적용되는 것처럼 서술했을 때만 true. 시행 예정 내용을 시행일과 함께 미래로 밝혔으면 false. [시점 사실]이 없으면 false.
3. 이유는 한 문장으로 쓴다.

[근거]
{context}

[질문]
{question}

[답변]
{answer}

[주장 목록]
{claims}

[시점 사실 — 기준일 {as_of}]
{facts}

[출력 형식 — JSON 하나만]
{{"claims": [{{"index": 1, "supported": true, "reason": "..."}}], "temporal_error": false, "temporal_reason": "..."}}"""
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["claims", "temporal_error", "temporal_reason"],
          "properties": {"claims": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["index", "supported", "reason"],
              "properties": {"index": {"type": "integer"}, "supported": {"type": "boolean"}, "reason": {"type": "string"}}}},
              "temporal_error": {"type": "boolean"}, "temporal_reason": {"type": "string"}}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-calls", type=int, default=0, help="hard cap on judge calls this run; 0 = no cap")
    args = ap.parse_args()
    gold = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval/gold/gold_v2.jsonl").open()}
    load = lambda p: {r["id"]: r for r in map(json.loads, p.open()) if r}
    jobs = []
    for run in args.runs:
        preds, judg = load(run / "predictions.jsonl"), load(run / "judgments.jsonl")
        for i, p in preds.items():
            claims = [c["claim"] for c in judg.get(i, {}).get("grounding", {}).get("claims", [])]
            if p["status"] != "answered" or not claims:
                continue
            g = gold[i]
            facts = temporal_facts(g) if g["level"] == "L4" else []
            ctx = "\n\n".join(c["text"] for c in p["meta"].get("context") or [])
            jobs.append({"run": run.name, "id": i, "level": g["level"], "claims": claims, "temporal": bool(facts),
                         "luna": {"claims": [bool(c.get("supported")) for c in judg[i]["grounding"]["claims"]],
                                  "temporal_error": judg[i].get("grade", {}).get("temporal_error")},
                         "prompt": PROMPT.format(context=ctx, question=g["question"], answer=p["answer"],
                                                 claims="\n".join(f"{n}. {c}" for n, c in enumerate(claims, 1)),
                                                 as_of=g["as_of"], facts="\n".join(f"- {f}" for f in facts) or "(없음)")})
    cache = Cache(f"grounding_{args.name}")
    budget, lock, codex_down = {"made": 0, "capped": 0}, threading.Lock(), threading.Event()

    def call(fn):
        def run_call(prompt: str) -> dict:
            if fn is codex and codex_down.is_set():
                return {"error": "skipped: codex failed earlier in this run"}
            with lock:
                if args.max_calls and budget["made"] >= args.max_calls:
                    budget["capped"] += 1
                    return {"error": f"skipped: --max-calls {args.max_calls} reached"}
                budget["made"] += 1
            res = fn(prompt, SYSTEM) if fn is opus else fn(prompt, SCHEMA)
            if fn is codex and "error" in res and not codex_down.is_set():
                codex_down.set()
                print(f"CODEX_FAILED {res['error'][-200:]!r} — further Codex calls skipped, Opus continues", flush=True)
            return res
        return run_call

    def verdict(res: dict, n: int) -> list:
        by = {int(c["index"]): bool(c["supported"]) for c in res.get("claims", []) if "index" in c}
        return [by.get(k) for k in range(1, n + 1)]

    def grade(job: dict) -> dict:
        o, c = cache.get(job, "opus", call(opus)), cache.get(job, "codex", call(codex))
        n = len(job["claims"])
        out = {k: v for k, v in job.items() if k != "prompt"}
        out["opus"] = {"claims": verdict(o, n), "temporal_error": o.get("temporal_error"), "reason": o.get("temporal_reason", "")}
        out["codex"] = {"claims": verdict(c, n), "temporal_error": c.get("temporal_error"), "reason": c.get("temporal_reason", "")}
        out["errors"] = {k: v["error"] for k, v in (("opus", o), ("codex", c)) if "error" in v}
        if None in out["opus"]["claims"] or None in out["codex"]["claims"]:
            out["errors"].setdefault("incomplete", "a claim verdict is missing")
        return out

    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(grade, jobs))
    missing = sum(bool(r["errors"]) for r in results)
    print(f"judge calls made {budget['made']}" + (f" / cap {args.max_calls}, skipped {budget['capped']}" if args.max_calls else ""))
    summary = {}
    if missing:
        print(f"{missing} answers lack a complete verdict — rerun to resume; no official Measure 5/6 published")
    else:
        for run in args.runs:
            rs = [r for r in results if r["run"] == run.name]
            m5 = {j: mean(sum(not x for x in r[j]["claims"]) / len(r["claims"]) for r in rs) for j in ("opus", "codex", "luna")}
            m5["official"] = mean(sum(not (a and b) for a, b in zip(r["opus"]["claims"], r["codex"]["claims"])) / len(r["claims"]) for r in rs)
            t = [r for r in rs if r["temporal"]]
            m6 = {j: mean(bool(r[j]["temporal_error"]) for r in t) for j in ("opus", "codex", "luna")} if t else {}
            if t:
                m6["official"] = mean(not (r["opus"]["temporal_error"] is False and r["codex"]["temporal_error"] is False) for r in t)
            summary[run.name] = {"answers": len(rs), "claims": sum(len(r["claims"]) for r in rs), "M5": m5,
                                 "case4_answers": len(t), "M6": m6}
        claims = [(a, b, l) for r in results for a, b, l in zip(r["opus"]["claims"], r["codex"]["claims"], r["luna"]["claims"])]
        summary["claim_agreement"] = {"n": len(claims), "opus=codex": sum(a == b for a, b, _ in claims),
                                      "opus=luna": sum(a == l for a, _, l in claims), "codex=luna": sum(b == l for _, b, l in claims)}
        for k, v in summary.items():
            print(k, json.dumps(v, ensure_ascii=False))
    path = ROOT / "eval/results" / f"grounding_{args.name}.json"
    path.write_text(json.dumps({"runs": [r.name for r in args.runs], "run_at": datetime.now().isoformat(timespec="seconds"),
                                "official": summary, "answers": results}, ensure_ascii=False, indent=1))
    print(path, len(results), "answers")


if __name__ == "__main__":
    main()
