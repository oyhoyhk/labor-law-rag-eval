"""Search and download Supreme Court precedents used to build L5 gold-set items.

Precedents are not part of the retrieval corpus (see docs/design.md §3.1); they
supply realistic fact patterns and expert-written holdings to grade against.

Usage:
  uv run python scripts/fetch_precedents.py search 해고예고 [--since 20150101]
  uv run python scripts/fetch_precedents.py fetch 600537 618229
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lawapi import search, service_xml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "precedents"


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", "\n", text or "")).strip()


def cmd_search(query: str, since: str) -> None:
    rows = search("prec", query, search=2)  # 2 = full-text search; default matches case names only
    rows = [r for r in rows if r.get("법원명") == "대법원" and r.get("선고일자", "").replace(".", "") >= since]
    for r in sorted(rows, key=lambda r: r["선고일자"], reverse=True):
        print(f"{r['판례일련번호']:>8}  {r['선고일자']}  {r['사건번호']:<14} {r['사건명']}")
    print(f"\n{len(rows)} Supreme Court cases (since {since})")


def cmd_fetch(ids: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for pid in ids:
        xml = service_xml("prec", ID=pid)
        root = ET.fromstring(xml)
        case_no = root.findtext("사건번호")
        if not case_no:
            print(f"{pid}: not found", file=sys.stderr)
            continue
        (OUT / f"{case_no}.xml").write_bytes(xml)
        print(f"== {case_no} ({root.findtext('선고일자')}) {root.findtext('사건명')}")
        print(f"참조조문: {clean(root.findtext('참조조문'))}")
        print(f"판시사항: {clean(root.findtext('판시사항'))[:300]}\n")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--since", default="20100101", help="YYYYMMDD lower bound on decision date")
    f = sub.add_parser("fetch")
    f.add_argument("ids", nargs="+", help="판례일련번호 values from `search`")
    args = p.parse_args()
    if args.cmd == "search":
        cmd_search(args.query, args.since)
    else:
        cmd_fetch(args.ids)


if __name__ == "__main__":
    main()
