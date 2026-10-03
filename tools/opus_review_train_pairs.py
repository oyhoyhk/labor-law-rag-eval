"""Second-opinion audit of the fine-tuning pair sample with Claude Opus via the `claude -p` CLI.

Usage: uv run python tools/opus_review_train_pairs.py   (after build_train_review_page.py wrote the sample)
Output: data/train/review_opus_v1.json  {pair id: {verdict: ok|bad|unsure, reason}}
"""

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
SRC = {"precedent": "대법원 판례의 판시사항(질문) → 그 판례의 참조조문(정답)", "synthetic": "LLM이 조문을 보고 만든 질문",
       "title": "조 제목(질문) → 그 조문(정답)"}


def judge(it: dict) -> tuple[str, dict]:
    pos = "\n\n".join(f"[{p['id']}]\n{p['text'][:2500]}" for p in it["positives"])
    prompt = PROMPT.format(source=SRC[it["source"]], query=it["query"], positives=pos)
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "json", "--system-prompt", SYSTEM,
           "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]
    for attempt in range(2):
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600, cwd=ROOT.parent)
        try:
            text = json.loads(proc.stdout)["result"]
            out = json.loads(text[text.find("{"):text.rfind("}") + 1])
            if out.get("verdict") in ("ok", "bad", "unsure"):
                return it["id"], {"verdict": out["verdict"], "reason": out.get("reason", "")}
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return it["id"], {"verdict": None, "reason": f"판정 실패: {proc.stderr[:120]}"}


def main() -> None:
    items = json.loads((ROOT / "data/train/review_sample_v1.json").read_text())
    with ThreadPoolExecutor(6) as ex:
        verdicts = dict(ex.map(judge, items))
    ver = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    (ROOT / "data/train/review_opus_v1.json").write_text(json.dumps(
        {"rater": "claude-opus", "cli": ver, "at": datetime.now().isoformat(timespec="seconds"),
         "verdicts": verdicts}, ensure_ascii=False, indent=1))
    from collections import Counter
    print(Counter((it["source"], verdicts[it["id"]]["verdict"]) for it in items))


if __name__ == "__main__":
    main()
