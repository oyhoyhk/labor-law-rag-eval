"""DELIBERATE OVERFITTING DEMO (eval-set leakage). NEVER ENABLE IN PRODUCTION.

`--fewshot-dev` reuses the dev split of the gold set as a few-shot example store: the 3 dev questions closest to
the query (KURE-v1 cosine) are added to the system prompt with their reference answers. A dev item retrieves
itself as example #1, i.e. the model reads the answer key. This exists only to check that the evaluation tells
"score raised by fitting the GT" apart from "real improvement" (docs/plans/2026-10-03-overfit-vs-generalize-
preregistration.md): dev should rise, test should not. It must never be on in the API or in any reported
system configuration.
"""

import json
from functools import lru_cache

import numpy as np

from app.index import embedder
from app.ingest.parse import ROOT

GOLD = ROOT / "eval" / "gold" / "gold_v2.jsonl"
SPLITS = ROOT / "eval" / "gold" / "splits.json"
N_EXAMPLES = 3


@lru_cache(maxsize=1)
def dev_items() -> list[dict]:
    splits = json.loads(SPLITS.read_text())
    items = [json.loads(l) for l in GOLD.open() if l.strip()]
    return [{"id": i["id"], "question": i["question"], "reference_answer": i["reference_answer"]}
            for i in items if splits.get(i["id"]) == "dev"]


@lru_cache(maxsize=1)
def dev_vectors() -> np.ndarray:
    return embedder().encode([d["question"] for d in dev_items()], normalize_embeddings=True,
                             convert_to_numpy=True).astype("float32")


def examples(question: str, n: int = N_EXAMPLES) -> list[dict]:
    q = embedder().encode([question], normalize_embeddings=True, convert_to_numpy=True).astype("float32")[0]
    sims = dev_vectors() @ q
    return [{**dev_items()[i], "score": float(sims[i])} for i in np.argsort(-sims, kind="stable")[:n]]


def section(question: str) -> str:
    """Appended to the system prompt. Question + reference answer only (no key points, no evidence ids)."""
    lines = ["", "[참고 예시] 비슷한 질문과 참고 답안입니다. 답변의 방식과 내용을 참고하세요."]
    for n, ex in enumerate(examples(question), 1):
        lines += ["", f"예시 {n}", f"질문: {ex['question']}", f"참고 답안: {ex['reference_answer']}"]
    return "\n".join(lines)
