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


def build() -> dict:
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())["documents"]
    current = {article_id(a.law, a.article_key): a for a in load_corpus("현행")}
    pending, sunsets, delegates = _pending(current, manifest), _sunsets(current, manifest), _delegations(current)
    delegated_from: dict[str, list[str]] = {}
    for child, parents in delegates.items():
        for p in parents:
            delegated_from.setdefault(p, []).append(child)
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
            "delegates_to": delegates.get(aid, []),
            "delegated_from": sorted(delegated_from.get(aid, [])),
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
    n_deleg = sum(bool(n["delegates_to"]) for n in g.values())
    print(f"{len(g)} nodes · {n_pending} with scheduled changes · {n_sunset} with sunsets · {n_deleg} delegating")
