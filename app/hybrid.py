"""Hybrid retrieval: dense (KURE-v1 FAISS) + character-bigram BM25, fused with Reciprocal Rank Fusion.

BM25 runs over the same chunks as the dense index of the chosen strategy, built lazily in memory.
Tokenization: tokens split at whitespace and punctuation, each token cut into Korean character bigrams
(a one-character token is kept whole). No morphological analyzer: legal terms ("통상임금", "제74조") match well
on surface form, and bigrams survive particles ("통상임금을" shares every bigram of "통상임금").

Refusal gate: every returned hit carries its *dense* cosine as "score", so the τ gate in app.rag keeps judging
the dense similarity of the fused top-1 hit. A hit that came only from BM25 (outside the dense top-N) has its
cosine computed directly from the stored vector — the gate never sees an RRF score.
"""

import math
import re
from collections import Counter
from functools import lru_cache

from app.index import Retriever, embedder

# Chosen on the dev split only (retrieval metrics, no LLM; eval.retrieval_check --grid --split dev):
# max Recall(all), tie-break MRR, over N ∈ {20, 50} × K ∈ {20, 60} × BM25 weight ∈ {0.5, 1.0}.
# Dev (n=40): best grid point Recall(all) 0.650 · MRR 0.807 vs dense-only 0.675 · 0.819 — no grid point beat dense.
CANDIDATES_N = 50  # dense top-N and BM25 top-N fed into the fusion
RRF_K = 60  # RRF constant K in w / (K + rank)
BM25_WEIGHT = 0.5  # dense weight is fixed at 1.0
BM25_K1, BM25_B = 1.5, 0.75


def tokenize(text: str) -> list[str]:
    out = []
    for tok in re.findall(r"\w+", text):  # whitespace and punctuation both separate tokens
        if len(tok) == 1:
            out.append(tok)
        out += [tok[i:i + 2] for i in range(len(tok) - 1)]
    return out


class BM25:
    def __init__(self, texts: list[str], k1: float = BM25_K1, b: float = BM25_B):
        self.k1, self.b = k1, b
        docs = [Counter(tokenize(t)) for t in texts]
        self.n = len(docs)
        self.lengths = [sum(d.values()) for d in docs]
        self.avgdl = sum(self.lengths) / self.n
        self.postings: dict[str, list[tuple[int, int]]] = {}
        for i, d in enumerate(docs):
            for tok, tf in d.items():
                self.postings.setdefault(tok, []).append((i, tf))
        self.idf = {t: math.log(1 + (self.n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def scores(self, query: str) -> dict[int, float]:
        out: dict[int, float] = {}
        for tok in set(tokenize(query)):
            for i, tf in self.postings.get(tok, []):
                norm = tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avgdl)
                out[i] = out.get(i, 0.0) + self.idf[tok] * tf * (self.k1 + 1) / norm
        return out

    def top(self, query: str, n: int) -> list[int]:
        s = self.scores(query)
        return sorted(s, key=lambda i: (-s[i], i))[:n]


def rrf(rankings: list[list[int]], weights: list[float], k: int) -> list[tuple[int, float]]:
    """Σ w_i / (k + rank_i) over the rankings an id appears in (rank from 1); best first, ties by smaller id."""
    score: dict[int, float] = {}
    for ranking, w in zip(rankings, weights):
        for rank, i in enumerate(ranking, 1):
            score[i] = score.get(i, 0.0) + w / (k + rank)
    return sorted(score.items(), key=lambda x: (-x[1], x[0]))


@lru_cache(maxsize=2)
def bm25(retriever: Retriever) -> BM25:
    return BM25([c["text"] for c in retriever.chunks])


def search(retriever: Retriever, query: str, k: int, n: int | None = None, rrf_k: int | None = None,
           bm25_weight: float | None = None) -> list[dict]:
    """Same output shape as Retriever.search; "score" is the dense cosine (see module docstring)."""
    n, rrf_k = n or CANDIDATES_N, rrf_k or RRF_K
    w = BM25_WEIGHT if bm25_weight is None else bm25_weight
    q = embedder().encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
    scores, idx = retriever.index.search(q, n)
    dense = {int(i): float(s) for s, i in zip(scores[0], idx[0]) if i >= 0}
    fused = rrf([list(dense), bm25(retriever).top(query, n)], [1.0, w], rrf_k)[:k]
    out = []
    for i, _ in fused:
        cos = dense[i] if i in dense else float(retriever.index.reconstruct(i) @ q[0])
        out.append({**retriever.chunks[i], "score": cos})
    return out
