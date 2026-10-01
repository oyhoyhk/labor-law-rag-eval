"""Two chunking strategies over the same articles (Part C H1).

- fixed:   each statute rendered as one stream, sliced into 512-token windows with
           64-token overlap — the common default, blind to article boundaries.
- article: one chunk per article (조) with a `[법령 > 장 > 조]` header; articles over
           the token cap are split at paragraph (항) boundaries, header repeated.

Both use the embedding model's own tokenizer so the token cap means the same thing.
Every chunk records the article ids it overlaps — that is what citations and
Evidence Recall@k are scored against.
"""

from dataclasses import dataclass, field

from app.ingest.parse import Article
from app.ingest.provision import article_id

MAX_TOKENS = 512
OVERLAP = 64


@dataclass
class Chunk:
    chunk_id: str
    law: str
    article_ids: list[str]
    text: str
    meta: dict = field(default_factory=dict)


def _n_tokens(tokenizer, text: str) -> int:
    return len(tokenizer(text, add_special_tokens=False)["input_ids"])


def article_chunks(articles: list[Article], tokenizer, max_tokens: int = MAX_TOKENS) -> list[Chunk]:
    out = []
    for a in articles:
        aid = article_id(a.law, a.article_key)
        header = "[" + " > ".join(x for x in (a.law, a.chapter, a.label) if x) + "]"
        blocks = []
        for p in a.paragraphs:
            block = "\n".join([p.text, *p.items])
            # A paragraph with many items (호) can exceed the cap alone; then split at item level.
            blocks += [p.text, *p.items] if _n_tokens(tokenizer, block) > max_tokens - 32 else [block]
        parts, cur = [], []
        for b in blocks:
            if cur and _n_tokens(tokenizer, "\n".join([header, *cur, b])) > max_tokens:
                parts.append(cur)
                cur = []
            cur.append(b)
        parts.append(cur)
        for i, part in enumerate(parts):
            cid = f"art:{aid}" + (f":{i + 1}" if len(parts) > 1 else "")
            out.append(Chunk(cid, a.law, [aid], "\n".join([header, *part]), {"part": i + 1, "parts": len(parts)}))
    return out


def fixed_chunks(articles: list[Article], tokenizer, size: int = MAX_TOKENS, overlap: int = OVERLAP) -> list[Chunk]:
    out = []
    by_law: dict[str, list[Article]] = {}
    for a in articles:
        by_law.setdefault(a.law, []).append(a)
    for law, arts in by_law.items():
        text, spans = "", []
        for a in arts:
            start = len(text)
            text += a.render() + "\n\n"
            spans.append((start, len(text), article_id(a.law, a.article_key)))
        enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        offsets = enc["offset_mapping"]
        step = size - overlap
        for i, t0 in enumerate(range(0, max(len(offsets) - overlap, 1), step)):
            t1 = min(t0 + size, len(offsets))
            c0, c1 = offsets[t0][0], offsets[t1 - 1][1]
            ids = [aid for s, e, aid in spans if s < c1 and e > c0]
            out.append(Chunk(f"fixed:{law}:{i}", law, ids, text[c0:c1].strip(), {"chars": [c0, c1]}))
    return out
