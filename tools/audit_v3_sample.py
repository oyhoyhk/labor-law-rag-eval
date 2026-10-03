"""Opus spot-check of the v3 additions before training: do multi questions really need both articles, and do case
questions point at their article (and stand out from the retriever's competitors)?

Usage: uv run python tools/audit_v3_sample.py
Output: data/train/review_v3_opus.json
"""

import json
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROMPT = """검색 모델 학습용 (질문, 정답 조문) 쌍을 검수합니다.
- answers: 질문의 답(핵심 근거)이 정답 조문에 있는가
- needs_all: 정답 조문이 여러 개일 때, 완전한 답에 그 조문들이 모두 필요한가 (하나만으로 충분하면 false, 정답이 1개면 true)
- distinct: 질문만 보고 아래 경쟁 조문보다 정답 조문이 더 맞는 검색 결과인가

질문: {query}

정답 조문:
{pos}

경쟁 조문:
{comp}

JSON으로만 답: {{"answers": true|false, "needs_all": true|false, "distinct": true|false, "reason": "한 문장"}}"""
CMD = ["claude", "-p", "--model", "opus", "--output-format", "json", "--tools", "", "--setting-sources", "",
       "--strict-mcp-config", "--no-session-persistence"]


def main() -> None:
    from app.ingest.parse import load_corpus
    from app.rag import retriever
    texts = {f"{a.law}#{a.article_key}": a.render() for a in load_corpus("현행")}
    ret = retriever("whole")
    rows = [json.loads(l) for l in (ROOT / "data/train/pairs_v3.jsonl").open()]
    rng = random.Random(11)
    sample = rng.sample([r for r in rows if r["source"].startswith("multi")], 15) + rng.sample([r for r in rows if r["source"] == "case"], 15)

    def judge(r):
        comp = [a for h in ret.search(r["query"], 12) for a in h["article_ids"] if a not in r["positives"]][:5]
        prompt = PROMPT.format(query=r["query"], pos="\n\n".join(f"[{a}]\n{texts[a][:3000]}" for a in r["positives"]),
                               comp="\n\n".join(f"[{a}]\n{texts[a][:1000]}" for a in comp))
        for _ in range(2):
            p = subprocess.run(CMD, input=prompt, capture_output=True, text=True, timeout=600, cwd=ROOT.parent)
            try:
                t = json.loads(p.stdout)["result"]
                return {"id": r["id"], "source": r["source"], "query": r["query"], **json.loads(t[t.find("{"):t.rfind("}") + 1])}
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        return {"id": r["id"], "source": r["source"], "query": r["query"], "error": True}

    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(judge, sample))
    (ROOT / "data/train/review_v3_opus.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for kind in ("multi", "case"):
        xs = [x for x in res if x["source"].startswith(kind) and "error" not in x]
        ok = [x for x in xs if x["answers"] and x["needs_all"] and x["distinct"]]
        print(kind, f"usable {len(ok)}/{len(xs)}", {k: sum(bool(x[k]) for x in xs) for k in ("answers", "needs_all", "distinct")})


if __name__ == "__main__":
    main()
