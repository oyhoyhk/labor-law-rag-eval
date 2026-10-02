"""Supreme Court precedents (law.go.kr XML) → one record per case.

The canonical text of a precedent is 판시사항 + 판결요지. When 판결요지 is empty (some cases publish only the
reasoning), the opening of 이유 is used instead, so a holding is always present. Gold-set literals, the precedent
index and the context block all use this same text.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREC_DIR = ROOT / "data" / "raw" / "precedents"
FALLBACK_CHARS = 1500


def _clean(text: str | None) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "")
    text = re.sub(r"[ \t　]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def precedent_id(case_no: str) -> str:
    """Evidence id: 판례#<first case number>, e.g. 판례#2020다247190 (joined cases keep the first number)."""
    return "판례#" + case_no.split(",")[0].strip()


@dataclass
class Precedent:
    id: str
    case_no: str
    decided: str
    title: str
    ref_articles: str  # raw 참조조문 string; parsed into corpus article ids by the provision graph
    issues: str  # 판시사항
    holding: str  # 판결요지, or the opening of 이유 when 판결요지 is empty
    holding_from_reasons: bool

    def render(self) -> str:
        return f"[판례] 대법원 {self.decided} 선고 {self.case_no} 판결 ({self.title})\n[판시사항]\n{self.issues}\n[판결요지]\n{self.holding}"


def parse(path: Path) -> Precedent:
    r = ET.parse(path).getroot()
    case_no = _clean(r.findtext("사건번호"))
    holding, from_reasons = _clean(r.findtext("판결요지")), False
    if not holding:
        body = _clean(r.findtext("판례내용"))
        start = body.find("이유")
        holding, from_reasons = body[start if start >= 0 else 0:][:FALLBACK_CHARS], True
    d = _clean(r.findtext("선고일자"))
    decided = f"{d[:4]}-{d[4:6]}-{d[6:8]}" if re.fullmatch(r"\d{8}", d) else d
    return Precedent(id=precedent_id(case_no), case_no=case_no, decided=decided, title=_clean(r.findtext("사건명")),
                     ref_articles=_clean(r.findtext("참조조문")), issues=_clean(r.findtext("판시사항")),
                     holding=holding, holding_from_reasons=from_reasons)


# 참조조문 → corpus article ids. A law name carries over a comma/slash list until the next name; 항·호 are dropped.
# "구 X(… 개정되기 전의 것)" links to the current article of the same number, unless the note says the law was
# wholly rewritten since (전부/전문 개정), when article numbers no longer line up.
_PAREN = re.compile(r"\([^()]*\)")
_ARTICLE = re.compile(r"제(\d+)조(?:의(\d+))?")
_REWRITTEN = "\x00rewritten\x00"


def ref_article_ids(ref: str, corpus: set[str]) -> list[str]:
    """Corpus article ids (<law>#<key>) cited in a 참조조문 string, in order of appearance; other laws are ignored."""
    laws = {re.sub(r"\s+", "", aid.split("#")[0]): aid.split("#")[0] for aid in corpus}
    text = re.sub(r"\[[^\]]*\]", " ", ref).replace("·", "ㆍ")
    while (stripped := _PAREN.sub(lambda m: _REWRITTEN if re.search(r"전[부문]\s*개정", m.group()) else " ", text)) != text:
        text = stripped
    out, law = [], None
    for seg in re.split(r"[,/]", text):
        m = _ARTICLE.search(seg)
        if not m:
            continue
        if name := seg[:m.start()].strip():
            name = re.sub(r"^구\s*", "", name)
            law = None if _REWRITTEN in name else laws.get(re.sub(r"\s+", "", name))
        if law:
            aid = f"{law}#{m.group(1)}" + (f"의{m.group(2)}" if m.group(2) else "")
            if aid in corpus and aid not in out:
                out.append(aid)
    return out


def load_precedents(directory: Path = PREC_DIR) -> dict[str, Precedent]:
    out = {}
    for path in sorted(directory.glob("*.xml")):
        p = parse(path)
        out.setdefault(p.id, p)
    return out
