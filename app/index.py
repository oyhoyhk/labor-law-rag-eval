"""Build and query a FAISS index per chunking strategy.

Usage: uv run python -m app.index build --strategy article|fixed
"""

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from datetime import date
from functools import lru_cache

import faiss
from sentence_transformers import SentenceTransformer

from app.ingest.chunk import Chunk, article_chunks, fixed_chunks
from app.ingest.parse import ROOT, load_corpus, parse_file
from app.ingest.provision import GRAPH, build as build_graph

EMBED_MODEL = "nlpai-lab/KURE-v1"
EMBED_REVISION = "8b418a58414668e75532ed045c22d9ca018ae2b2"
INDEX_DIR = ROOT / "data" / "index"


@lru_cache(maxsize=1)
def embedder() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL, revision=EMBED_REVISION, device="mps")


def _future_only_articles(graph: dict) -> list:
    """Articles that exist only in a scheduled version (e.g. a newly inserted 조)."""
    out = []
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())["documents"]
    wanted = {aid for aid, n in graph["nodes"].items() if not n["in_current"]}
    for d in manifest:
        if d["status"] != "시행예정" or not wanted:
            continue
        for a in parse_file(ROOT / d["path"], d["name"]):
            if (aid := f"{a.law}#{a.article_key}") in wanted:
                out.append(a)
                wanted.discard(aid)
    return out


def build(strategy: str) -> None:
    graph = json.loads(GRAPH.read_text()) if GRAPH.exists() else build_graph()
    articles = load_corpus("현행") + _future_only_articles(graph)
    model = embedder()
    chunker = article_chunks if strategy == "article" else fixed_chunks
    chunks: list[Chunk] = chunker(articles, model.tokenizer)

    t0 = time.time()
    emb = model.encode([c.text for c in chunks], batch_size=16, normalize_embeddings=True,
                       show_progress_bar=True, convert_to_numpy=True).astype("float32")
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)

    out = INDEX_DIR / strategy
    out.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out / "faiss.index"))
    with (out / "chunks.jsonl").open("w") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    manifest_hash = hashlib.sha256((ROOT / "data" / "manifest.json").read_bytes()).hexdigest()[:12]
    meta = {"strategy": strategy, "embed_model": EMBED_MODEL, "embed_revision": EMBED_REVISION,
            "chunks": len(chunks), "dim": int(emb.shape[1]), "built_at": date.today().isoformat(),
            "corpus_manifest_sha256": manifest_hash, "encode_seconds": round(time.time() - t0, 1)}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(meta, ensure_ascii=False))


class Retriever:
    def __init__(self, strategy: str = "article"):
        d = INDEX_DIR / strategy
        self.strategy = strategy
        self.index = faiss.read_index(str(d / "faiss.index"))
        self.chunks = [json.loads(line) for line in (d / "chunks.jsonl").open()]
        self.meta = json.loads((d / "meta.json").read_text())

    def search(self, query: str, k: int = 5) -> list[dict]:
        q = embedder().encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        scores, idx = self.index.search(q, k)
        return [{**self.chunks[i], "score": float(s)} for s, i in zip(scores[0], idx[0]) if i >= 0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--strategy", choices=["article", "fixed"], default="article")
    args = ap.parse_args()
    build(args.strategy)
