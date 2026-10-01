"""Parse law.go.kr eflaw XML into article records.

One record per article (조). Paragraph (항) and item (호/목) text is kept both
structured and rendered, so chunking can choose its own granularity.
"""

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "manifest.json"

AMEND_TAG = re.compile(r"<(개정|신설|전문개정|본조신설)\s+([\d.,\s]+)>")
DATE = re.compile(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})")
HEADING = re.compile(r"^제\d+조(의\d+)?(\([^)]*\))?\s*")


@dataclass
class Paragraph:
    no: str  # "①" or "" for single-paragraph articles
    text: str
    items: list[str] = field(default_factory=list)


@dataclass
class Article:
    law: str  # e.g. "근로기준법 시행령"
    law_id: str
    level: str  # 법률 | 시행령 | 시행규칙
    version_effective: str  # YYYYMMDD of the whole version
    article_key: str  # "60" or "43의2"
    title: str
    chapter: str
    effective: str  # 조문시행일자
    paragraphs: list[Paragraph]
    amended: list[str]  # ISO dates from <개정/신설 ...> tags

    @property
    def label(self) -> str:
        num, _, branch = self.article_key.partition("의")
        return f"제{num}조" + (f"의{branch}" if branch else "") + (f"({self.title})" if self.title else "")

    def render(self) -> str:
        lines = [f"{self.law} {self.label}"]
        for p in self.paragraphs:
            lines.append(p.text)
            lines.extend(f"  {i}" for i in p.items)
        return "\n".join(lines)


def _text(e: ET.Element | None, tag: str) -> str:
    return (e.findtext(tag) or "").strip() if e is not None else ""


def _items(node: ET.Element) -> list[str]:
    out = []
    for ho in node.findall("호"):
        out.append(_text(ho, "호내용"))
        out.extend("  " + _text(mok, "목내용") for mok in ho.findall("목"))
    return [i for i in out if i.strip()]


def _amend_dates(text: str) -> list[str]:
    dates = []
    for _, body in AMEND_TAG.findall(text):
        dates += [f"{y}-{int(m):02d}-{int(d):02d}" for y, m, d in DATE.findall(body)]
    return dates


def level_of(name: str) -> str:
    return "시행규칙" if name.endswith("시행규칙") else "시행령" if name.endswith("시행령") else "법률"


def parse_file(path: Path, name: str) -> list[Article]:
    root = ET.parse(path).getroot()
    info = root.find("기본정보")
    law_id, version_eff = _text(info, "법령ID"), _text(info, "시행일자")
    chapter, articles = "", []
    for u in root.iter("조문단위"):
        if _text(u, "조문여부") == "전문":  # 편/장/절 heading, not an article
            chapter = _text(u, "조문내용")
            continue
        key = _text(u, "조문번호") + (f"의{_text(u, '조문가지번호')}" if _text(u, "조문가지번호") else "")
        paras = [Paragraph(_text(h, "항번호"), _text(h, "항내용"), _items(h)) for h in u.findall("항")]
        head = _text(u, "조문내용")
        if not paras:  # single-paragraph article: body lives in 조문내용 after the heading
            paras = [Paragraph("", HEADING.sub("", head, count=1), [])]
        elif not any(p.text for p in paras):  # 항 without 항내용 holds only 호 items
            paras = [Paragraph("", head, [i for p in paras for i in p.items])]
        all_text = head + " " + " ".join(p.text + " " + " ".join(p.items) for p in paras)
        articles.append(Article(
            law=name, law_id=law_id, level=level_of(name), version_effective=version_eff,
            article_key=key, title=_text(u, "조문제목"), chapter=chapter,
            effective=_text(u, "조문시행일자"), paragraphs=paras, amended=sorted(set(_amend_dates(all_text))),
        ))
    return articles


def load_corpus(status: str = "현행") -> list[Article]:
    """All articles from manifest documents with the given status (현행 | 시행예정)."""
    manifest = json.loads(MANIFEST.read_text())
    out = []
    for d in manifest["documents"]:
        if d["status"] == status:
            out += parse_file(ROOT / d["path"], d["name"])
    return out


def article_to_dict(a: Article) -> dict:
    return asdict(a) | {"label": a.label, "text": a.render()}
