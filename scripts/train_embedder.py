"""Fine-tune the retrieval embedder on (query, article) pairs — the gold set is never read here.

Each pairs_v2 row expands to one (anchor, positive[, hard negative]) example per positive article.
Hard negative: the highest-ranked article from the base retriever that is not a positive and not linked to one
(delegation parent/implementing), so a correct-but-unlabelled article is not pushed away.
Loss: MultipleNegativesRankingLoss with a no-duplicate sampler (the same query never shares a batch with itself).

Usage:
  uv run python scripts/train_embedder.py --name kure-ft-v1
  uv run python scripts/train_embedder.py --name kure-ft-noprec --sources title,synthetic
  uv run python scripts/train_embedder.py --name kure-ft-f25 --frac 0.25
  uv run python scripts/train_embedder.py --name qwen3-4b-lora --base Qwen/Qwen3-Embedding-4B --bf16 --lora-r 16 \
      --query-prefix "$INSTRUCTION" --no-hard-negative      # LoRA, merged into the base before saving
Output: models/<name>/ (+ train_meta.json); then `python -m app.index build --strategy whole --model models/<name>`
"""

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from datasets import Dataset  # noqa: E402
from sentence_transformers import SentenceTransformerTrainer, SentenceTransformerTrainingArguments  # noqa: E402
from sentence_transformers.losses import CachedMultipleNegativesRankingLoss, MultipleNegativesRankingLoss  # noqa: E402
from sentence_transformers.training_args import BatchSamplers  # noqa: E402

from app.index import EMBED_MODEL, EMBED_REVISION, Retriever, embedder  # noqa: E402
from app.ingest.parse import load_corpus  # noqa: E402


def linked(graph: dict, aid: str) -> set:
    n = graph.get(aid, {})
    return set(n.get("implementing_provisions", [])) | set(n.get("parent_provisions", []))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--pairs", default="data/train/pairs_v2.jsonl")
    ap.add_argument("--sources", default="precedent,title,synthetic")
    ap.add_argument("--frac", type=float, default=1.0, help="subsample pairs (learning curve)")
    ap.add_argument("--epochs", type=float, default=1)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--no-hard-negative", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--base", default=EMBED_MODEL, help="hub id of the model to fine-tune")
    ap.add_argument("--query-prefix", default="", help="instruction/prefix put before every query (as at query time)")
    ap.add_argument("--bf16", action="store_true", help="load the base in bfloat16")
    ap.add_argument("--lora-r", type=int, default=0, help="LoRA rank on attention projections; 0 = full fine-tune")
    ap.add_argument("--mini-batch", type=int, default=0,
                    help="CachedMNRL mini-batch: keep the in-batch negatives of --batch but compute in chunks (big models)")
    ap.add_argument("--grad-ckpt", action="store_true", help="gradient checkpointing (big models)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    srcs = set(args.sources.split(","))
    pairs = [json.loads(l) for l in (ROOT / args.pairs).open()]
    pairs = [p for p in pairs if p["source"] in srcs]
    if args.frac < 1:
        pairs = rng.sample(pairs, int(len(pairs) * args.frac))
    texts = {f"{a.law}#{a.article_key}": a.render() for a in load_corpus("현행")}
    graph = json.loads((ROOT / "data/processed/provision_graph.json").read_text())["nodes"]
    base = Retriever("whole") if not args.no_hard_negative else None

    rows = []
    for p in pairs:
        pos = [a for a in p["positives"] if a in texts]
        block = set(pos) | {x for a in pos for x in linked(graph, a)}
        neg = None
        if base:
            neg = next((a for h in base.search(p["query"], 15) for a in h["article_ids"] if a not in block and a in texts), None)
        for a in pos:
            row = {"anchor": args.query_prefix + p["query"], "positive": texts[a]}
            if base:
                row["negative"] = texts[neg] if neg else texts[rng.choice([x for x in texts if x not in block])]
            rows.append(row)
    rng.shuffle(rows)
    print(f"{len(pairs)} pairs → {len(rows)} examples", flush=True)

    model = embedder(args.base, EMBED_REVISION if args.base == EMBED_MODEL else None, args.bf16)
    model.max_seq_length = args.max_len
    if args.lora_r:
        from peft import LoraConfig, get_peft_model
        cfg = LoraConfig(r=args.lora_r, lora_alpha=2 * args.lora_r, lora_dropout=0.05,
                         target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
        model[0].model = get_peft_model(model[0].model, cfg)  # ST 6: auto_model is a read-only view of .model
        model[0].model.print_trainable_parameters()
    if args.grad_ckpt:
        model[0].model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        if args.lora_r:
            model[0].model.enable_input_require_grads()
    out = ROOT / "models" / args.name
    targs = SentenceTransformerTrainingArguments(
        output_dir=str(out / "checkpoints"), num_train_epochs=args.epochs, per_device_train_batch_size=args.batch,
        learning_rate=args.lr, warmup_steps=0.1, batch_sampler=BatchSamplers.NO_DUPLICATES, seed=args.seed,
        save_strategy="no", logging_steps=20, report_to="none", dataloader_drop_last=True,
        bf16=torch.cuda.is_available())
    t0 = time.time()
    SentenceTransformerTrainer(model=model, args=targs, train_dataset=Dataset.from_list(rows),
                               loss=(CachedMultipleNegativesRankingLoss(model, mini_batch_size=args.mini_batch)
                                     if args.mini_batch else MultipleNegativesRankingLoss(model))).train()
    if args.lora_r:  # store a plain model so indexing/serving need no peft
        model[0].model = model[0].model.merge_and_unload()
    model.save(str(out))
    data_sha = hashlib.sha256((ROOT / args.pairs).read_bytes()).hexdigest()[:12]
    meta = {"name": args.name, "base": args.base, "base_revision": EMBED_REVISION if args.base == EMBED_MODEL else None,
            "lora_r": args.lora_r, "query_prefix": args.query_prefix, "bf16": args.bf16,
            "mini_batch": args.mini_batch, "grad_ckpt": args.grad_ckpt, "pairs": args.pairs,
            "pairs_sha256": data_sha, "sources": sorted(srcs), "frac": args.frac, "n_pairs": len(pairs),
            "n_examples": len(rows), "hard_negative": base is not None, "epochs": args.epochs, "lr": args.lr,
            "batch": args.batch, "max_len": args.max_len, "seed": args.seed, "train_seconds": round(time.time() - t0)}
    (out / "train_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
