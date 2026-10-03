"""Per-article notes for the audit sample: for each labelled positive, its role for the query (core / related /
unrelated), the sentence that makes it so, and a one-line note. Helps a reviewer see which of several positives
actually carries the answer (precedent pairs inherit every 참조조문, including ones cited for other issues).

Usage: uv run python tools/annotate_positives.py
Output: data/train/review_positive_notes_v1.json  {pair id: [{article, role, quote, note}]}
"""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = """검색 학습용 (질문, 정답 조문들) 쌍입니다. 정답 조문 각각이 이 질문에 대해 어떤 역할인지 판정하세요.
- core: 질문의 답 또는 핵심 근거가 이 조문에 있음
- related: 질문 주제와 관련은 있으나 답을 직접 주지 않음(정의 일부, 절차, 벌칙 등)
- unrelated: 질문과 무관(다른 쟁점에서 인용된 조문 등)

질문: {query}

{positives}

JSON 한 개로만 답: {{"notes": [{{"article": "조문 ID", "role": "core|related|unrelated", "quote": "판단 근거가 된 조문 속 구절(30자 이내, 원문 그대로, 없으면 빈 문자열)", "note": "한국어 한 문장, 명사형 종결"}}]}}"""


def annotate(it: dict) -> tuple[str, list]:
    pos = "\n\n".join(f"[{p['id']}]\n{p['text'][:4000]}" for p in it["positives"])
    cmd = ["claude", "-p", "--model", "opus", "--output-format", "json", "--tools", "", "--setting-sources", "",
           "--strict-mcp-config", "--no-session-persistence"]
    for _ in range(2):
        proc = subprocess.run(cmd, input=PROMPT.format(query=it["query"], positives=pos), capture_output=True,
                              text=True, timeout=600, cwd=ROOT.parent)
        try:
            text = json.loads(proc.stdout)["result"]
            return it["id"], json.loads(text[text.find("{"):text.rfind("}") + 1])["notes"]
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return it["id"], []


def main() -> None:
    items = json.loads((ROOT / "data/train/review_sample_v1.json").read_text())
    with ThreadPoolExecutor(6) as ex:
        notes = dict(ex.map(annotate, items))
    (ROOT / "data/train/review_positive_notes_v1.json").write_text(json.dumps(notes, ensure_ascii=False, indent=1))
    from collections import Counter
    print(Counter(n.get("role") for v in notes.values() for n in v), "missing", [k for k, v in notes.items() if not v])


if __name__ == "__main__":
    main()
