"""Condense the Opus and Codex audit reasons into short per-model key points, and explain each disagreement.
A summarization pass over the two models' own reasons — no new verdicts.

Usage: uv run python tools/summarize_review_views.py [--version v1|v2]
Output: data/train/review_views_<version>.json  {pair id: {opus_point, codex_point, why_differ}}
"""

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = """두 모델(Opus, Codex)이 검색 학습용 (질문, 정답 조문) 쌍을 같은 기준으로 판정하고 남긴 이유입니다.
판정 기준: ok = 질문의 답·핵심 근거가 정답 조문에 있음, bad = 답할 수 없거나 질문이 학습에 못 쓸 만큼 어색함, unsure = 관련은 있으나 간접적·다른 조문이 더 적합.

각 쌍마다 아래를 작성하세요. 새로 판정하지 말고 주어진 이유만 요약·비교합니다.
- opus_point, codex_point: 각 모델 이유의 핵심을 25자 이내 명사형으로
- why_differ: 두 판정이 다를 때만, 두 모델이 서로 다른 무엇을 우선했는지 한 문장(명사형 종결). 같으면 빈 문자열

JSON 한 개로만 답: {{"<id>": {{"opus_point": "...", "codex_point": "...", "why_differ": "..."}}, ...}}

{items}"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1", choices=["v1", "v2"])
    v = ap.parse_args().version
    sample = json.loads((ROOT / "data/train/review_sample_v1.json").read_text())
    opus = json.loads((ROOT / f"data/train/review_opus_{v}.json").read_text())["verdicts"]
    codex = json.loads((ROOT / f"data/train/review_codex_{v}.json").read_text())["verdicts"]
    lines = []
    for it in sample:
        o, c = opus[it["id"]], codex[it["id"]]
        sub = lambda j: f" (답변={j.get('answers')}, 구별={j.get('distinct')})" if "answers" in j else ""
        lines.append(f"[{it['key']}] 출처={it['source']} 질문={it['query']}\n  정답 조문={', '.join(p['id'] for p in it['positives'])}\n"
                     f"  Opus={o['verdict']}{sub(o)}: {o['reason']}\n  Codex={c['verdict']}{sub(c)}: {c['reason']}")
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "json", "--tools", "", "--setting-sources", "",
           "--strict-mcp-config", "--no-session-persistence"]
    proc = subprocess.run(cmd, input=PROMPT.format(items="\n\n".join(lines)), capture_output=True, text=True,
                          timeout=900, cwd=ROOT.parent)
    text = json.loads(proc.stdout)["result"]
    views = json.loads(text[text.find("{"):text.rfind("}") + 1])
    by_key = {it["key"]: it["id"] for it in sample}
    out = {by_key[k]: v for k, v in views.items() if k in by_key}
    (ROOT / f"data/train/review_views_{v}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out), "views")


if __name__ == "__main__":
    main()
