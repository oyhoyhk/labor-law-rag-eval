"""Second-opinion audit of the fine-tuning pair sample with Claude Opus via the `claude -p` CLI.

Usage: uv run python tools/opus_review_train_pairs.py [--version v1|v2]   (after build_train_review_page.py)
Output: data/train/review_opus_<version>.json  {pair id: {verdict: ok|bad|unsure, reason}}

v1: positive articles only (2,500 chars each). v2: adds the 5 articles the current retriever ranks highest
(competitors) and splits the criterion into "answers the question" and "singled out among competitors" —
v1 left the second to each judge's own knowledge, which is where Opus and Codex diverged.
"""

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = "당신은 한국 노동법 전문가로서 검색 모델 학습 데이터의 라벨을 검수합니다. 지시한 JSON 한 개만 출력합니다."
PROMPT = """임베딩 검색 모델 학습용 (질문, 정답 조문) 쌍입니다. "이 질문을 받으면 검색 시스템이 이 조문을 찾아오는 것이 맞는가"를 판정하세요.

판정 기준
- ok: 질문의 답 또는 핵심 근거가 정답 조문(여러 개면 그중 하나 이상)에 있음
- bad: 정답 조문으로는 답할 수 없음, 또는 질문이 어색하거나 무의미해 학습에 쓸 수 없음
- unsure: 관련은 있으나 다른 조문이 더 적합하거나, 판례 쟁점과 조문의 관련이 간접적임

출처: {source}
질문: {query}

정답 조문:
{positives}

JSON으로만 답: {{"verdict": "ok|bad|unsure", "reason": "한국어 한 문장, 명사형 종결"}}"""
PROMPT_V2 = """임베딩 검색 모델 학습용 (질문, 정답 조문) 쌍입니다. 검색 대상은 노동법령 24건의 조문 894개입니다.
아래 두 조건을 모두 판정하세요.

조건 A (답변): 질문의 답 또는 핵심 근거가 정답 조문(여러 개면 그중 하나 이상)에 있는가
조건 B (구별): 질문만 보고, 아래 '경쟁 조문'보다 정답 조문이 더 맞는 검색 결과라고 할 수 있는가
  - 경쟁 조문은 현재 검색기가 이 질문에 대해 상위로 가져온 다른 조문
  - 질문이 법령을 특정하지 않아 경쟁 조문도 똑같이 정답이 될 수 있으면 B 불충족

판정
- ok: A와 B 모두 충족
- unsure: A는 충족하나 B가 애매함(경쟁 조문과 비슷하게 맞음), 또는 A가 간접적(판례 쟁점의 일부만 조문과 관련)
- bad: A 불충족, 또는 B 명백히 불충족(경쟁 조문과 구별 불가), 또는 질문이 무의미

출처: {source}
질문: {query}

정답 조문:
{positives}

경쟁 조문:
{competitors}

JSON으로만 답: {{"verdict": "ok|bad|unsure", "answers": true|false, "distinct": true|false, "reason": "한국어 한 문장, 명사형 종결, 판단에 쓴 조문 내용을 근거로"}}"""
LIMIT = {"v1": 2500, "v2": 4000}
COMP_LIMIT = 1200


def build_prompt(it: dict, version: str) -> str:
    pos = "\n\n".join(f"[{p['id']}]\n{p['text'][:LIMIT[version]]}" for p in it["positives"])
    if version == "v1":
        return PROMPT.format(source=SRC[it["source"]], query=it["query"], positives=pos)
    comp = "\n\n".join(f"[{c['id']}]\n{c['text'][:COMP_LIMIT]}" for c in it.get("competitors", [])) or "(없음)"
    return PROMPT_V2.format(source=SRC[it["source"]], query=it["query"], positives=pos, competitors=comp)


SRC = {"precedent": "대법원 판례의 판시사항(질문) → 그 판례의 참조조문(정답)", "synthetic": "LLM이 조문을 보고 만든 질문",
       "title": "조 제목(질문) → 그 조문(정답)"}


def judge(it: dict, version: str = "v1") -> tuple[str, dict]:
    prompt = build_prompt(it, version)
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "json", "--system-prompt", SYSTEM,
           "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]
    for attempt in range(2):
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600, cwd=ROOT.parent)
        try:
            text = json.loads(proc.stdout)["result"]
            out = json.loads(text[text.find("{"):text.rfind("}") + 1])
            if out.get("verdict") in ("ok", "bad", "unsure"):
                return it["id"], {k: out.get(k) for k in ("verdict", "answers", "distinct", "reason") if k in out}
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return it["id"], {"verdict": None, "reason": f"판정 실패: {proc.stderr[:120]}"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1", choices=list(LIMIT))
    args = ap.parse_args()
    items = json.loads((ROOT / "data/train/review_sample_v1.json").read_text())
    with ThreadPoolExecutor(6) as ex:
        verdicts = dict(ex.map(lambda it: judge(it, args.version), items))
    ver = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    (ROOT / f"data/train/review_opus_{args.version}.json").write_text(json.dumps(
        {"rater": "claude-opus", "prompt": args.version, "cli": ver, "at": datetime.now().isoformat(timespec="seconds"),
         "verdicts": verdicts}, ensure_ascii=False, indent=1))
    from collections import Counter
    print(Counter((it["source"], verdicts[it["id"]]["verdict"]) for it in items))


if __name__ == "__main__":
    main()
