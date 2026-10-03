"""Judge every precedent pair with Claude Opus (`claude -p`): per-article role + answers/distinct, one call per pair.

The rule validated against the human-confirmed sample (data/train/review_human_v1.json):
  keep the pair iff answers and distinct;  training positives = articles judged core.

Usage:
  uv run python tools/judge_precedent_pairs.py --validate     # the 15 human-confirmed precedent pairs only
  uv run python tools/judge_precedent_pairs.py                # all precedent pairs, resumable
Output: data/train/precedent_judgments_v1.jsonl (one JSON per pair, appended as it goes)
"""

import argparse
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/train/precedent_judgments_v1.jsonl"
SYSTEM = "당신은 한국 노동법 전문가로서 검색 모델 학습 데이터의 라벨을 검수합니다. 지시한 JSON 한 개만 출력합니다."
PROMPT = """임베딩 검색 모델 학습용 쌍입니다. 질문은 대법원 판례의 판시사항(쟁점), 정답 후보는 그 판례의 참조조문입니다.
검색 대상은 노동법령 24건의 조문 894개입니다.

1) 정답 후보 조문 각각의 역할
- core: 질문의 답 또는 핵심 근거가 이 조문에 있음
- related: 주제는 관련되나 답을 직접 주지 않음(정의 일부, 절차, 벌칙 등)
- unrelated: 질문과 무관(판례가 다른 쟁점에서 인용한 조문 등)

2) 쌍 전체 (사람 확정 표본으로 검증한 판정 v2와 같은 기준)
- answers (조건 A): 질문의 답 또는 핵심 근거가 정답 후보 조문(여러 개면 그중 하나 이상)에 있는가
- distinct (조건 B): 질문만 보고 아래 경쟁 조문보다 정답 후보 조문이 더 맞는 검색 결과라고 할 수 있는가
  (질문이 법령을 특정하지 않아 경쟁 조문도 똑같이 정답이 될 수 있으면 false)

질문: {query}

정답 후보 조문:
{positives}

경쟁 조문(현재 검색기가 이 질문에 상위로 가져온 다른 조문):
{competitors}

JSON으로만 답: {{"roles": [{{"article": "조문 ID", "role": "core|related|unrelated"}}], "answers": true|false, "distinct": true|false, "reason": "한국어 한 문장, 명사형 종결"}}"""
CMD = ["claude", "-p", "--model", "opus", "--output-format", "json", "--system-prompt", SYSTEM, "--tools", "",
       "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]
STOP_AFTER = 3  # consecutive failures → stop and look (do not burn through the queue)


def load_inputs(only_ids: set | None):
    from app.ingest.parse import load_corpus
    from app.rag import retriever
    texts = {f"{a.law}#{a.article_key}": a.render() for a in load_corpus("현행")}
    ret = retriever("whole")
    rows = [json.loads(l) for l in (ROOT / "data/train/pairs_v1.jsonl").open()]
    rows = [r for r in rows if r["source"] == "precedent" and (only_ids is None or r["id"] in only_ids)]
    for r in rows:
        pos = set(r["positives"])
        comp = [a for h in ret.search(r["query"], 12) for a in h["article_ids"] if a not in pos]
        r["pos_text"] = {a: texts.get(a, "") for a in r["positives"]}
        r["competitors"] = [(a, texts.get(a, "")) for a in dict.fromkeys(comp)][:5]
    return rows


def judge(r: dict) -> dict | None:
    pos = "\n\n".join(f"[{a}]\n{t[:4000]}" for a, t in r["pos_text"].items())
    comp = "\n\n".join(f"[{a}]\n{t[:1200]}" for a, t in r["competitors"]) or "(없음)"
    prompt = PROMPT.format(query=r["query"], positives=pos, competitors=comp)
    for _ in range(2):
        proc = subprocess.run(CMD, input=prompt, capture_output=True, text=True, timeout=600, cwd=ROOT.parent)
        try:
            text = json.loads(proc.stdout)["result"]
            out = json.loads(text[text.find("{"):text.rfind("}") + 1])
            roles = {x["article"]: x["role"] for x in out["roles"] if x.get("article") in r["pos_text"]}
            if roles and isinstance(out.get("answers"), bool) and isinstance(out.get("distinct"), bool):
                core = [a for a in r["positives"] if roles.get(a) == "core"]
                return {"id": r["id"], "query": r["query"], "roles": roles, "answers": out["answers"],
                        "distinct": out["distinct"], "reason": out.get("reason", ""),
                        "keep": out["answers"] and out["distinct"] and bool(core), "positives": core}
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    human = json.loads((ROOT / "data/train/review_human_v1.json").read_text())
    if args.validate:
        target = {h["pair"]: h for h in human.values() if h["source"] == "precedent"}
        rows = load_inputs(set(target))
        with ThreadPoolExecutor(args.workers) as ex:
            res = [x for x in ex.map(judge, rows) if x]
        keep_ok = sum(x["keep"] == (not target[x["id"]]["excluded"]) for x in res)
        kept = [x for x in res if not target[x["id"]]["excluded"] and x["keep"]]
        sel_ok = sum(set(x["positives"]) == set(target[x["id"]]["selected"]) for x in kept)
        print(f"validated {len(res)}/{len(rows)} · keep agrees {keep_ok}/{len(res)} · "
              f"positives agree {sel_ok}/{len(kept)} (both kept)")
        for x in res:
            h = target[x["id"]]
            if x["keep"] != (not h["excluded"]) or (x["keep"] and set(x["positives"]) != set(h["selected"])):
                print("  diff", x["id"], "model keep", x["keep"], x["positives"], "| human", not h["excluded"], h["selected"])
        return
    done = {json.loads(l)["id"] for l in OUT.open()} if OUT.exists() else set()
    rows = [r for r in load_inputs(None) if r["id"] not in done]
    print(f"{len(done)} done, {len(rows)} to go", flush=True)
    lock, fails = threading.Lock(), [0]
    stop = threading.Event()

    def work(r):
        if stop.is_set():
            return
        res = judge(r)
        with lock:
            if res is None:
                fails[0] += 1
                print("FAIL", r["id"], flush=True)
                if fails[0] >= STOP_AFTER:
                    stop.set()
                return
            fails[0] = 0
            with OUT.open("a") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, rows))
    total = sum(1 for _ in OUT.open())
    print(("STOPPED after consecutive failures · " if stop.is_set() else "") + f"{total} judged", flush=True)


if __name__ == "__main__":
    main()
