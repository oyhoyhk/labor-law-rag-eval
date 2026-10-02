"""Provision graph: effectivity status and links for every current article.

Sources, in order of trust:
1. Official scheduled versions (시행예정) — diffed article by article against the
   chain current → v1 → v2 …; each change carries an official effective date.
2. 부칙 sunset clauses ("…까지 효력을 가진다") — the only expiry signal, since the
   official current text still prints expired paragraphs (e.g. 근로기준법 제53조③).
3. Delegation links (시행령 "법 제N조" → 법률, 시행규칙 "영 제N조" → 시행령).

Status is never computed by the LLM; `status_at()` renders it for a given date.
"""

import difflib
import json
import re
import xml.etree.ElementTree as ET
from datetime import date

from app.ingest.parse import ROOT, Article, level_of, load_corpus, parse_file

GRAPH = ROOT / "data" / "processed" / "provision_graph.json"

SUNSET = re.compile(
    r"제(\d+)조(?:의(\d+))?((?:제\d+항)?(?:\s*및\s*제\d+항)*)의 개정규정(\s*중[^은]*)?은\s*"
    r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일까지 효력을 가진다"
)
PARA_NO = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
DELEGATION = re.compile(r"(법|영) 제(\d+)조(?:의(\d+))?")


def article_id(law: str, key: str) -> str:
    return f"{law}#{key}"


def _body(a: Article) -> list[str]:
    return [p.text + "".join(p.items) for p in a.paragraphs]


def _iso(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def _pending(current: dict[str, Article], manifest: list[dict]) -> dict[str, list[dict]]:
    """Diff each statute's version chain; returns article_id -> scheduled changes."""
    out: dict[str, list[dict]] = {}
    by_law: dict[str, list[dict]] = {}
    for d in manifest:
        if d["status"] == "시행예정":
            by_law.setdefault(d["name"], []).append(d)
    for law, versions in by_law.items():
        prev = {a.article_key: a for a in current.values() if a.law == law}
        for d in sorted(versions, key=lambda d: (d["effective"], d["promulgated"])):
            nxt = {a.article_key: a for a in parse_file(ROOT / d["path"], law)}
            for key in sorted(set(prev) | set(nxt)):
                old, new = prev.get(key), nxt.get(key)
                if old and new and _body(old) == _body(new):
                    continue
                kind = "added" if old is None else "deleted" if new is None else "modified"
                changed = []
                if old and new:
                    sm = difflib.SequenceMatcher(a=_body(old), b=_body(new))
                    changed = [new.paragraphs[j].text for tag, *_, j1, j2 in sm.get_opcodes()
                               if tag != "equal" for j in range(j1, j2)]
                eff = new.effective if new and new.effective > d["effective"] else d["effective"]
                out.setdefault(article_id(law, key), []).append({
                    "kind": kind,
                    "effective": _iso(eff),
                    "promulgated": _iso(d["promulgated"]),
                    "promulgation_no": d["promulgation_no"],
                    "changed_paragraphs": changed,
                    "new_text": new.render() if new else None,
                })
            prev = nxt
    return out


def _sunsets(current: dict[str, Article], manifest: list[dict]) -> dict[str, list[dict]]:
    """Expiry clauses that still bind a paragraph present in the current text."""
    out: dict[str, list[dict]] = {}
    for d in manifest:
        if d["status"] != "현행":
            continue
        root = ET.parse(ROOT / d["path"]).getroot()
        for unit in root.iter("부칙단위"):
            promulgated = _iso(unit.findtext("부칙공포일자") or "")
            text = re.sub(r"\s+", " ", "".join(unit.itertext()))
            for m in SUNSET.finditer(text):
                key = m.group(1) + (f"의{m.group(2)}" if m.group(2) else "")
                art = current.get(article_id(d["name"], key))
                if art is None:
                    continue
                paras = [PARA_NO[int(n) - 1] for n in re.findall(r"제(\d+)항", m.group(3) or "")]
                targets = [p for p in art.paragraphs if p.no in paras] if paras else art.paragraphs
                # Skip if the paragraph was rewritten after this 부칙 — the sunset no longer binds it.
                if not targets or _rewritten_after(targets, promulgated):
                    continue
                out.setdefault(article_id(d["name"], key), []).append({
                    "paragraphs": paras,
                    "until": f"{m.group(5)}-{int(m.group(6)):02d}-{int(m.group(7)):02d}",
                    "partial": bool(m.group(4)),
                    "source": f"부칙({promulgated})",
                    "clause": m.group(0),
                })
    return out


def _rewritten_after(paragraphs, promulgated: str) -> bool:
    for p in paragraphs:
        dates = [f"{y}-{int(mo):02d}-{int(d):02d}"
                 for y, mo, d in re.findall(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", p.text)]
        if any(d > promulgated for d in dates):
            return True
    return False


def _delegations(current: dict[str, Article]) -> dict[str, list[str]]:
    """시행령/시행규칙 article -> the parent provisions it cites (법 제N조 / 영 제N조)."""
    out: dict[str, list[str]] = {}
    for aid, a in current.items():
        if a.level == "법률":
            continue
        base = a.law.removesuffix(" 시행령").removesuffix(" 시행규칙")
        text = " ".join(_body(a))
        for kind, num, branch in DELEGATION.findall(text):
            parent = base if kind == "법" else f"{base} 시행령"
            pid = article_id(parent, num + (f"의{branch}" if branch else ""))
            if pid in current and pid not in out.get(aid, []):
                out.setdefault(aid, []).append(pid)
    return out


# Same-law references. Each "제N조" either continues the enumeration before it ("제7조, 제9조, 제20조부터
# 제22조까지") and inherits its law, or starts a new one whose law is named by the preceding word: 「…」, 법, 영,
# 시행령, 징수법, 같은 법 … mean another (or the parent) law — except "이 법/영/규칙", which is this one.
REF = re.compile(r"제(\d+)조(?:의(\d+))?")
CONTINUATION = re.compile(r"(?:\s|[,ㆍ·]|및|또는|와|과|부터|까지|제\d+(?:항|호)|의\d+|[가-하]목|본문|단서|전단|후단"
                          r"|같은 조|같은 항|각 호 외의 부분|\([^()]*\))*")
OTHER_LAW_PREFIX = re.compile(r"(」|법|영|시행령|규칙|」\s*\(이하[^()]*\))$")  # incl. 「…」(이하 "…법"이라 한다)
SAME_LAW_PREFIX = re.compile(r"이\s+(법|영|규칙)$")
# Cue strength: an exception/exclusion or an extension (준용) of the referenced article, else plain.
CUES = [("exception", re.compile(r"적용하지\s*(아니|않)|에도\s*불구하고|제외(한|하)|예외로\s*한다")),
        ("mutatis", re.compile(r"준용(한다|하며|하고|된다)"))]
CUE_RANK = {"exception": 0, "mutatis": 1, "plain": 2}


def _cue(sentence: str) -> str:
    return next((name for name, rx in CUES if rx.search(sentence)), "plain")


def _sentences(a: Article) -> list[str]:
    """Paragraph sentences; an item (호) is read together with its paragraph's lead text, which carries its cue."""
    out = []
    for p in a.paragraphs:
        out += re.split(r"(?<=다\.)\s+", p.text)
        out += [p.text + " " + i for i in p.items]
    return out


def _same_law_refs(sentence: str) -> list[str]:
    """Article keys of this law referenced in one sentence; "제55조부터 제57조까지" expands to 55·56·57."""
    keys, prev, same = [], None, False
    for m in REF.finditer(sentence):
        between = sentence[prev.end():m.start()] if prev else None
        if between is None or not CONTINUATION.fullmatch(between):
            before = sentence[:m.start()].rstrip()
            same = not OTHER_LAW_PREFIX.search(before) or bool(SAME_LAW_PREFIX.search(before))
        elif same and "부터" in between and not prev.group(2) and not m.group(2):
            keys += [str(n) for n in range(int(prev.group(1)) + 1, int(m.group(1))) if int(m.group(1)) - int(prev.group(1)) <= 10]
        if same:
            keys.append(m.group(1) + (f"의{m.group(2)}" if m.group(2) else ""))
        prev = m
    return keys


def _references(current: dict[str, Article]) -> dict[str, dict[str, str]]:
    """article -> {referenced same-law article: strongest cue}. Delegation (법/영 제N조) and 「other law」 refs excluded."""
    out: dict[str, dict[str, str]] = {}
    for aid, a in current.items():
        for sent in _sentences(a):
            cue = _cue(sent)
            for key in _same_law_refs(sent):
                tid = article_id(a.law, key)
                if tid == aid or tid not in current:
                    continue
                refs = out.setdefault(aid, {})
                if tid not in refs or CUE_RANK[cue] < CUE_RANK[refs[tid]]:
                    refs[tid] = cue
    return out


def build() -> dict:
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())["documents"]
    current = {article_id(a.law, a.article_key): a for a in load_corpus("현행")}
    pending, sunsets, delegates = _pending(current, manifest), _sunsets(current, manifest), _delegations(current)
    references = _references(current)
    implementing_provisions: dict[str, list[str]] = {}
    for child, parents in delegates.items():
        for p in parents:
            implementing_provisions.setdefault(p, []).append(child)
    referenced_by: dict[str, dict[str, str]] = {}
    for src, targets in references.items():
        for tid, cue in targets.items():
            referenced_by.setdefault(tid, {})[src] = cue
    nodes = {}
    for aid in set(current) | set(pending):
        a = current.get(aid)
        nodes[aid] = {
            "law": a.law if a else aid.split("#")[0],
            "level": a.level if a else level_of(aid.split("#")[0]),
            "label": a.label if a else None,
            "in_current": a is not None,
            "pending": pending.get(aid, []),
            "sunsets": sunsets.get(aid, []),
            "parent_provisions": delegates.get(aid, []),
            "implementing_provisions": sorted(implementing_provisions.get(aid, [])),
            # Same-law article references; *_cues hold the strongest cue (exception | mutatis | plain) per edge.
            "references": sorted(references.get(aid, {})),
            "reference_cues": dict(sorted(references.get(aid, {}).items())),
            "referenced_by": sorted(referenced_by.get(aid, {})),
            "referenced_by_cues": dict(sorted(referenced_by.get(aid, {}).items())),
        }
    graph = {"built_at": date.today().isoformat(), "nodes": nodes}
    GRAPH.parent.mkdir(parents=True, exist_ok=True)
    GRAPH.write_text(json.dumps(graph, ensure_ascii=False, indent=1))
    return graph


def status_at(node: dict, as_of: str) -> dict:
    """Effectivity of one article on `as_of` (YYYY-MM-DD), with human-readable notes."""
    notes, status = [], "in_force" if node["in_current"] else "pending"
    for s in node["sunsets"]:
        target = "·".join(s["paragraphs"]) or "전체"
        if s["partial"]:
            notes.append(f"일부 효력기한 있음({target}, {s['until']}까지): {s['clause']}")
            status = status if status != "in_force" else "unknown"
        elif s["until"] < as_of:
            notes.append(f"제{target}항 효력 상실({s['until']}까지 유효, {s['source']})")
            status = "partially_expired" if s["paragraphs"] else "expired"
    for p in node["pending"]:
        if p["effective"] > as_of:
            notes.append(f"{p['effective']} 시행 예정 {p['kind']} (공포 {p['promulgated']})")
            if status == "in_force":
                status = "amendment_pending"
    return {"status": status, "notes": notes}


if __name__ == "__main__":
    g = build()["nodes"]
    n_pending = sum(bool(n["pending"]) for n in g.values())
    n_sunset = sum(bool(n["sunsets"]) for n in g.values())
    n_impl = sum(bool(n["parent_provisions"]) for n in g.values())
    print(f"{len(g)} nodes · {n_pending} with scheduled changes · {n_sunset} with sunsets · {n_impl} implementing a parent provision")
    cues = [c for n in g.values() for c in n["reference_cues"].values()]
    print(f"{len(cues)} same-law reference edges ({sum(c == 'exception' for c in cues)} exception · "
          f"{sum(c == 'mutatis' for c in cues)} 준용 · {sum(c == 'plain' for c in cues)} plain) "
          f"from {sum(bool(n['references']) for n in g.values())} articles")
