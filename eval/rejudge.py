"""Re-grade key points of disputed items with two independent judges (Opus via `claude -p`, Codex via `codex exec`).

Disputed = answerable items that failed M0 in any of the given runs; every run's answer to those items is
re-graded (also the passing ones, so judge consistency across near-identical answers is visible).
The judges see question, key points and answer only — never the Luna verdicts.

Answered refusal-expected items (out-of-scope questions) are graded on one fixed point, HEDGE_POINT: the answer
says the material cannot decide the question instead of asserting a conclusion (Luna's asserts_conclusion=false).
The official M0 (2026-10-04, Luna dropped as judge) counts an answerable item correct only when Opus AND Codex
find every key point, and a refusal-expected item correct when it was refused or both judges accept the hedge.

Usage: uv run python -m eval.rejudge NAME runs/a runs/b runs/c [--all] [--reuse eval/results/rejudge_X.json] [--workers 4] [--max-calls N]
  --all    every answered answerable item, not only the disputed ones (absolute score under Opus/Codex)
  --max-calls N  hard cap on judge calls this run (cache hits are free); past it calls are skipped, not cached,
                 and no official score is published — rerun with a higher cap to resume
Output: eval/results/rejudge_<NAME>.json
Every successful verdict is appended to eval/results/rejudge_cache/<NAME>.jsonl as soon as it returns, so an
interrupted run (quota, crash) resumes with only the missing (run, item, judge) calls; failed calls are not cached. (per answer: Luna / Opus / Codex key-point verdicts and reasons)
"""

import argparse
import hashlib
import json
import threading
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEX_MODEL = "gpt-6-astra"
SYSTEM = ("You are a strict grader of a Korean labor-law QA system. Use only the given key points and answer; "
          "never your own legal knowledge. Output exactly one JSON object and nothing else.")
PROMPT = """한국 노동법령 QA 시스템의 답변이 각 정답 포인트(key point)를 담고 있는지 채점하세요. 자신의 법률 지식은 쓰지 말고 정답 포인트와 답변만 비교하세요.

[판정 규칙]
- 답변이 그 사실을 명시적으로 단언하면 true. 표현이 달라도 의미(수치·기간·날짜·조건·주체·의무/재량)가 같으면 true.
- 다르거나 반대이거나 언급이 없거나 앞뒤가 모순되면 false.
- 정답 포인트가 여러 사실을 담고 있으면(예: 날짜와 내용) 핵심 사실이 모두 있어야 true. 빠진 부분은 reason에 적으세요.
- 각 포인트를 독립적으로 판정하고, 판정 근거가 된 답변 문장을 quote에 그대로 옮기세요(없으면 빈 문자열).

[질문]
{question}

[정답 포인트]
{key_points}

[답변]
{answer}

[출력 형식 — JSON 하나만]
{{"key_points": [{{"index": 1, "asserted": true, "quote": "...", "reason": "한 문장"}}]}}"""
HEDGE_POINT = ("질문이 묻는 사항의 근거가 제공된 자료에 없다는 점(묻는 제도·규정이 없다는 점 포함)을 밝히고, "
               "그 근거 없이 질문에 대한 결론(예/아니오, 허용 여부 등)을 단정하지 않음")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["key_points"],
          "properties": {"key_points": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["index", "asserted", "quote", "reason"],
              "properties": {"index": {"type": "integer"}, "asserted": {"type": "boolean"},
                             "quote": {"type": "string"}, "reason": {"type": "string"}}}}}}


def parse(text: str) -> dict:
    return json.loads(text[text.find("{"):text.rfind("}") + 1])


def opus(prompt: str) -> dict:
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "json", "--system-prompt", SYSTEM,
           "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]
    for attempt in range(2):
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600, cwd=ROOT.parent)
        try:
            return parse(json.loads(proc.stdout)["result"])
        except (json.JSONDecodeError, KeyError, ValueError):
            if attempt:
                return {"error": (proc.stdout + proc.stderr)[-300:]}


def codex(prompt: str) -> dict:
    prompt = "파일을 읽거나 명령을 실행하지 말고, 아래 내용만 보고 판정하세요.\n\n" + prompt
    with tempfile.TemporaryDirectory() as d:  # empty working dir: no repo files or AGENTS.md
        schema, out = Path(d) / "schema.json", Path(d) / "out.json"
        schema.write_text(json.dumps(SCHEMA))
        cmd = ["codex", "exec", "-m", CODEX_MODEL, "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "-C", d,
               "--output-schema", str(schema), "-o", str(out), "-"]
        for _ in range(2):
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600)
            try:
                return json.loads(out.read_text())
            except (OSError, json.JSONDecodeError):
                pass
    return {"error": proc.stderr[-300:]}


def verdicts(res: dict, n: int) -> list:
    by = {int(k["index"]): k for k in res.get("key_points", [])}
    return [{"ok": by[i]["asserted"], "quote": by[i].get("quote", ""), "reason": by[i].get("reason", "")} if i in by
            else None for i in range(1, n + 1)]


class Cache:
    """Append-only verdict cache keyed by (run, item, judge, prompt hash)."""

    def __init__(self, name: str):
        self.path = ROOT / "eval/results/rejudge_cache" / f"{name}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.hits = {}
        if self.path.exists():
            for line in self.path.open():
                r = json.loads(line)
                self.hits[(r["run"], r["id"], r["judge"], r["prompt_sha"])] = r["result"]

    def get(self, job: dict, judge: str, call) -> dict:
        sha = hashlib.sha256(job["prompt"].encode()).hexdigest()[:16]
        key = (job["run"], job["id"], judge, sha)
        if key in self.hits:
            return self.hits[key]
        res = call(job["prompt"])
        if "error" not in res:
            with self.lock:
                self.hits[key] = res
                with self.path.open("a") as f:
                    f.write(json.dumps({"run": key[0], "id": key[1], "judge": judge, "prompt_sha": sha, "result": res},
                                       ensure_ascii=False) + "\n")
        return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--all", action="store_true", help="re-grade every answered answerable item")
    ap.add_argument("--reuse", type=Path, help="earlier rejudge output whose verdicts are kept for the same (run, item)")
    ap.add_argument("--max-calls", type=int, default=0, help="hard cap on judge CLI/API calls this run; 0 = no cap")
    args = ap.parse_args()
    gold = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval/gold/gold_v2.jsonl").open()}
    load = lambda p: {r["id"]: r for r in map(json.loads, p.open()) if r}
    runs = [(r, load(r / "scores.jsonl"), load(r / "predictions.jsonl"), load(r / "judgments.jsonl")) for r in args.runs]
    disputed = sorted({i for _, s, _, _ in runs for i, x in s.items()
                       if (x["expected"] == "answered" and (args.all or not x["m0_correct"])) or (args.all and x["expected"] != "answered")})
    reused = {(a["run"], a["id"]): a for a in json.loads(args.reuse.read_text())["answers"]} if args.reuse else {}
    cache = Cache(args.name)
    budget = {"made": 0, "capped": 0}
    budget_lock = threading.Lock()

    def capped(call):
        """Count real judge calls against --max-calls; refuse (uncached) once the cap is reached."""
        def run_call(prompt: str) -> dict:
            with budget_lock:
                if args.max_calls and budget["made"] >= args.max_calls:
                    budget["capped"] += 1
                    return {"error": f"skipped: --max-calls {args.max_calls} reached"}
                budget["made"] += 1
            return call(prompt)
        return run_call

    def codex_capped(prompt: str) -> dict:  # a Codex call skipped after a Codex failure is not counted
        return {"error": "skipped: codex failed earlier in this run"} if codex_down.is_set() else capped(codex_guarded)(prompt)
    codex_down = threading.Event()  # first Codex failure (e.g. usage limit) stops further Codex calls this run

    def codex_guarded(prompt: str) -> dict:
        if codex_down.is_set():
            return {"error": "skipped: codex failed earlier in this run"}
        res = codex(prompt)
        if "error" in res and not codex_down.is_set():
            codex_down.set()
            print(f"CODEX_FAILED {res['error'][-200:]!r} — further Codex calls skipped, Opus continues", flush=True)
        return res
    jobs = []
    for r, s, p, j in runs:
        for i in disputed:
            if s[i]["status"] != "answered":
                continue
            if gold[i]["expected_status"] == "answered":
                kps = gold[i]["key_points"]
                luna = {k["key_point"]: k for k in j.get(i, {}).get("grade", {}).get("key_points", [])}  # none with --no-judge
                luna_v = [{"ok": luna[k]["asserted"], "quote": luna[k].get("quote", "")} if k in luna else None for k in kps]
            else:  # answered although refusal was expected: did it hedge instead of concluding?
                kps = [HEDGE_POINT]
                ac = j.get(i, {}).get("grade", {}).get("asserts_conclusion")
                luna_v = [None if ac is None else {"ok": ac is False, "quote": ""}]
            jobs.append({"id": i, "run": r.name, "question": gold[i]["question"], "key_points": kps,
                         "expected": gold[i]["expected_status"], "answer": p[i]["answer"], "m0_luna": s[i]["m0_correct"],
                         "luna": luna_v,
                         "prompt": PROMPT.format(question=gold[i]["question"], answer=p[i]["answer"],
                                                 key_points="\n".join(f"{n}. {k}" for n, k in enumerate(kps, 1)))})

    def run(job: dict) -> dict:
        if (job["run"], job["id"]) in reused and not reused[(job["run"], job["id"])]["errors"]:
            return reused[(job["run"], job["id"])]
        n = len(job["key_points"])
        o, c = cache.get(job, "opus", capped(opus)), cache.get(job, "codex", codex_capped)
        out = {k: v for k, v in job.items() if k != "prompt"}
        out.update(opus=verdicts(o, n), codex=verdicts(c, n), errors={k: v["error"] for k, v in (("opus", o), ("codex", c)) if "error" in v})
        return out

    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(run, jobs))
    missing = sum(bool(r["errors"]) for r in results)
    print(f"judge calls made {budget['made']}" + (f" / cap {args.max_calls}, skipped {budget['capped']}" if args.max_calls else ""))
    if missing:  # do not publish a score with failed verdicts counted as wrong
        print(f"{missing} answers still lack a verdict ({sum('opus' in r['errors'] for r in results)} opus, "
              f"{sum('codex' in r['errors'] for r in results)} codex); cached {len(cache.hits)} verdicts — rerun to resume")
    for r in results:
        for judge in ("luna", "opus", "codex"):
            v = r[judge]
            r[f"m0_{judge}"] = all(x and x["ok"] for x in v) if v and None not in v else None
    official = {}
    if args.all and not missing:  # every item of every run is decided: refused items by rule, answered ones by both judges
        by = {(a["run"], a["id"]): a for a in results}
        for r, s, _, _ in runs:
            ok = [bool(by[(r.name, i)]["m0_opus"] and by[(r.name, i)]["m0_codex"]) if (r.name, i) in by
                  else (x["expected"] != "answered" and x["status"] != "answered") for i, x in s.items()]
            official[r.name] = {"M0_opus_and_codex": round(sum(ok) / len(ok), 3), "n": len(ok)}
        print("official M0 (Opus ∧ Codex):", {k.split("_", 1)[1]: v["M0_opus_and_codex"] for k, v in official.items()})
    path = ROOT / "eval/results" / f"rejudge_{args.name}.json"
    path.write_text(json.dumps({"runs": [r.name for r in args.runs], "disputed": disputed, "codex_model": CODEX_MODEL,
                                "run_at": datetime.now().isoformat(timespec="seconds"), "official": official,
                                "answers": results},
                               ensure_ascii=False, indent=1))
    agree = lambda a, b: sum(r[f"m0_{a}"] == r[f"m0_{b}"] for r in results)
    print(path, len(results), "answers ·", f"luna=opus {agree('luna', 'opus')} · luna=codex {agree('luna', 'codex')} · opus=codex {agree('opus', 'codex')}",
          "· errors", sum(bool(r["errors"]) for r in results))


if __name__ == "__main__":
    main()
