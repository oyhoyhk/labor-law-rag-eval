"""Closed-book probe: how much of the gold facts does the LLM answer with no retrieved context?

High closed-book accuracy means retrieval quality is masked by parametric knowledge.
Grading is deterministic: every `must` group needs at least one alternative in the answer.

Usage: uv run python scripts/closed_book_check.py [--repeats 1]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.llm import LLM  # noqa: E402

GOLD = ROOT / "eval" / "gold" / "closed_book_v0.jsonl"
SYSTEM = "당신은 한국 노동법 전문가입니다. 현재 시행 중인 한국 법령 기준으로 질문에 간결하게 답하세요. 모르면 모른다고 답하세요."


def grade(answer: str, must: list[list[str]]) -> bool:
    norm = answer.replace(" ", "")
    return all(any(alt.replace(" ", "") in norm for alt in group) for group in must)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    items = [json.loads(line) for line in GOLD.read_text().splitlines() if line.strip()]
    llm = LLM(budget_krw=50)
    out_dir = ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}_closed_book"
    out_dir.mkdir(parents=True)

    rows, score = [], defaultdict(lambda: [0, 0])
    for rep in range(args.repeats):
        for q in items:
            answer, usage = llm.chat(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q["question"]}],
                max_tokens=300,
            )
            ok = grade(answer, q["must"])
            score[q["era"]][0] += ok
            score[q["era"]][1] += 1
            rows.append({"repeat": rep, "id": q["id"], "era": q["era"], "correct": ok, "answer": answer,
                         "model": usage["model"]})
            print(f"{'O' if ok else 'X'} {q['id']} [{q['era']}] {answer[:90]!r}")

    (out_dir / "predictions.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    summary = {
        "model": llm.model, "repeats": args.repeats, "items": len(items),
        "accuracy": {era: round(c / n, 3) for era, (c, n) in score.items()},
        "overall": round(sum(c for c, _ in score.values()) / sum(n for _, n in score.values()), 3),
        "usage": vars(llm.usage), "cost_krw": round(llm.spent_krw, 2),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
