"""Build and query a FAISS index per chunking strategy.

Usage: uv run python -m app.index build --strategy article|whole|fixed|precedent
       uv run python -m app.index build --strategy whole --model models/kure-ft-v1   # → data/index/whole@kure-ft-v1

The precedent index embeds Precedent.render() and is used only to rank precedents that are already linked to a
retrieved article (never searched on its own).
"""

import argparse
import hashlib
import json
import threading
import time
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

from app.ingest.chunk import Chunk, article_chunks, fixed_chunks
from app.ingest.parse import ROOT, load_corpus, parse_file
from app.ingest.precedent import load_precedents
from app.ingest.provision import GRAPH, build as build_graph

EMBED_MODEL = "nlpai-lab/KURE-v1"
EMBED_REVISION = "8b418a58414668e75532ed045c22d9ca018ae2b2"
INDEX_DIR = ROOT / "data" / "index"
# eval runs answer items on worker threads; MPS (and one model instance in general) must not encode concurrently
ENCODE_LOCK = threading.Lock()
WHOLE_MAX_TOKENS = 8192  # KURE-v1 / XLM-R context; the longest 조 is ~2.5k tokens


@lru_cache(maxsize=4)
def embedder(model: str = EMBED_MODEL, revision: str | None = EMBED_REVISION, bf16: bool = False,
             trust_remote_code: bool = False) -> SentenceTransformer:
    """The base KURE-v1 by default; a fine-tuned local directory or another hub model when an index was built with one."""
    import torch
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    kwargs = {"torch_dtype": torch.bfloat16} if bf16 else {}
    m = SentenceTransformer(model, revision=revision, device=device, trust_remote_code=trust_remote_code,
                            model_kwargs=kwargs)
    # Fine-tuned models are saved with their training length; use the model's real context, capped at 8,192.
    limit = getattr(m.tokenizer, "model_max_length", WHOLE_MAX_TOKENS)
    m.max_seq_length = min(WHOLE_MAX_TOKENS, limit if limit and limit < 10**6 else WHOLE_MAX_TOKENS)
    return m


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


def build(strategy: str, model_path: str | None = None, query_prefix: str = "", doc_prefix: str = "",
          bf16: bool = False, trust_remote_code: bool = False) -> None:
    """model_path: a local fine-tuned directory or a hub id. Prefixes follow each model's card (e5: "query: " /
    "passage: ", Qwen3-Embedding: an instruction before the query); they are stored in meta and reused at query time."""
    graph = json.loads(GRAPH.read_text()) if GRAPH.exists() else build_graph()
    articles = load_corpus("현행") + _future_only_articles(graph)
    model_name, revision = (str(model_path), None) if model_path else (EMBED_MODEL, EMBED_REVISION)
    model = embedder(model_name, revision, bf16, trust_remote_code)
    if strategy == "whole":  # one vector per 조, no 항·호 split (longest 조 ≈ 2.5k tokens, model limit 8,192)
        chunks: list[Chunk] = article_chunks(articles, model.tokenizer, max_tokens=WHOLE_MAX_TOKENS)
    else:
        chunker = article_chunks if strategy == "article" else fixed_chunks
        chunks = chunker(articles, model.tokenizer)

    t0 = time.time()
    emb = model.encode([doc_prefix + c.text for c in chunks], batch_size=8 if bf16 else 16, normalize_embeddings=True,
                       show_progress_bar=True, convert_to_numpy=True).astype("float32")
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)

    out = INDEX_DIR / (f"{strategy}@{Path(model_path).name}" if model_path else strategy)
    out.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out / "faiss.index"))
    with (out / "chunks.jsonl").open("w") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    manifest_hash = hashlib.sha256((ROOT / "data" / "manifest.json").read_bytes()).hexdigest()[:12]
    meta = {"strategy": strategy, "embed_model": model_name, "embed_revision": revision,
            "query_prefix": query_prefix, "doc_prefix": doc_prefix, "bf16": bf16, "trust_remote_code": trust_remote_code,
            "max_seq_length": model.max_seq_length, "chunks": len(chunks), "dim": int(emb.shape[1]), "built_at": date.today().isoformat(),
            "corpus_manifest_sha256": manifest_hash, "encode_seconds": round(time.time() - t0, 1)}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(meta, ensure_ascii=False))


def build_precedents() -> None:
    precs = list(load_precedents().values())
    t0 = time.time()
    emb = embedder().encode([p.render() for p in precs], batch_size=8, normalize_embeddings=True,
                            show_progress_bar=True, convert_to_numpy=True).astype("float32")
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    out = INDEX_DIR / "precedent"
    out.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out / "faiss.index"))
    (out / "ids.json").write_text(json.dumps([p.id for p in precs], ensure_ascii=False) + "\n")
    meta = {"strategy": "precedent", "embed_model": EMBED_MODEL, "embed_revision": EMBED_REVISION,
            "precedents": len(precs), "dim": int(emb.shape[1]), "built_at": date.today().isoformat(),
            "encode_seconds": round(time.time() - t0, 1)}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(meta, ensure_ascii=False))


class PrecedentScorer:
    """Cosine similarity between a query and given precedents (no search over the whole set)."""

    def __init__(self):
        d = INDEX_DIR / "precedent"
        index = faiss.read_index(str(d / "faiss.index"))
        ids = json.loads((d / "ids.json").read_text())
        self.vectors = {pid: index.reconstruct(i) for i, pid in enumerate(ids)}

    def scores(self, query: str, ids: list[str]) -> dict[str, float]:
        with ENCODE_LOCK:
            q = embedder().encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")[0]
        return {pid: float(self.vectors[pid] @ q) for pid in ids if pid in self.vectors}


class Retriever:
    def __init__(self, strategy: str = "article"):
        d = INDEX_DIR / strategy
        self.strategy = strategy
        self.index = faiss.read_index(str(d / "faiss.index"))
        self.chunks = [json.loads(line) for line in (d / "chunks.jsonl").open()]
        self.meta = json.loads((d / "meta.json").read_text())
        m = self.meta
        self.model = embedder(m.get("embed_model", EMBED_MODEL), m.get("embed_revision", EMBED_REVISION),
                              m.get("bf16", False), m.get("trust_remote_code", False))
        self.query_prefix = m.get("query_prefix", "")

    def search(self, query: str, k: int = 5) -> list[dict]:
        with ENCODE_LOCK:
            q = self.model.encode([self.query_prefix + query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        scores, idx = self.index.search(q, k)
        return [{**self.chunks[i], "score": float(s)} for s, i in zip(scores[0], idx[0]) if i >= 0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--strategy", choices=["article", "whole", "fixed", "precedent"], default="article")
    b.add_argument("--model", help="local fine-tuned directory or hub id (index goes to <strategy>@<last path part>)")
    b.add_argument("--query-prefix", default="")
    b.add_argument("--doc-prefix", default="")
    b.add_argument("--bf16", action="store_true")
    b.add_argument("--trust-remote-code", action="store_true")
    args = ap.parse_args()
    if args.strategy == "precedent":
        build_precedents()
    else:
        build(args.strategy, args.model, args.query_prefix, args.doc_prefix, args.bf16, args.trust_remote_code)
