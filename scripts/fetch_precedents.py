"""Search and download Supreme Court precedents.

Precedents supply L5 gold-set fact patterns and are reached at query time through the
article → precedent links of the provision graph (참조조문), never as free search hits.

Usage:
  uv run python scripts/fetch_precedents.py search 해고예고 [--since 20150101]
  uv run python scripts/fetch_precedents.py fetch 600537 618229
  uv run python scripts/fetch_precedents.py bulk [--max 400]   # every corpus statute + core topics
"""

import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lawapi import search, service_xml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "precedents"
SUPREME_COURT = "400201"  # 법원종류코드 for 대법원
TOPICS = ["해고", "통상임금", "연차", "퇴직금", "파견", "기간제", "최저임금", "성희롱", "육아휴직", "임금체불"]


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


def _search_all(query: str, since: str) -> list[dict]:
    """Every Supreme Court full-text hit since `since`, newest first, across all result pages."""
    rows, page = [], 1
    while True:
        batch = search("prec", query, search=2, org=SUPREME_COURT, prncYd=f"{since}~{date.today():%Y%m%d}",
                       sort="ddes", page=page)
        rows += [r for r in batch if r.get("법원명") == "대법원" and r.get("선고일자", "").replace(".", "") >= since]
        if len(batch) < 100:
            return rows
        page += 1
        time.sleep(0.5)


def _entry(root: ET.Element, query: str) -> dict:
    return {"serial": root.findtext("판례정보일련번호"), "case_no": root.findtext("사건번호"),
            "decided": root.findtext("선고일자"), "title": root.findtext("사건명"), "query": query,
            "fetched_at": date.today().isoformat()}


def cmd_bulk(since: str, cap: int) -> None:
    """Fetch precedents for every corpus statute, then core topics, until `cap` cases are on disk.

    Queries run smallest result set first, so niche statutes are covered in full and only the largest
    (근로기준법) is truncated — newest decisions first.
    """
    laws = sorted(p.name for p in (ROOT / "data" / "raw" / "laws").iterdir()
                  if p.is_dir() and not p.name.endswith(("시행령", "시행규칙")))
    have = {path.stem.split(",")[0] for path in OUT.glob("*.xml")}
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"cases": []}
    listed = {c["case_no"] for c in manifest["cases"]}
    for path in sorted(OUT.glob("*.xml")):  # cases fetched by hand (gold set) before the bulk run
        root = ET.parse(path).getroot()
        if root.findtext("사건번호") not in listed:
            manifest["cases"].append(_entry(root, "manual"))
    known = {c["serial"] for c in manifest["cases"]}
    try:
        _bulk_fetch(laws, since, cap, have, known, manifest)
    finally:  # keep the manifest in sync with the files even if a request fails midway
        manifest.update(source="law.go.kr DRF prec", since=since, cap=cap)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(have)} precedents on disk · {len(manifest['cases'])} in manifest")


def _bulk_fetch(laws: list[str], since: str, cap: int, have: set, known: set, manifest: dict) -> None:
    for queries in (laws, TOPICS):
        results = {q: _search_all(q, since) for q in queries}
        for q in sorted(results, key=lambda q: len(results[q])):
            print(f"{q}: {len(results[q])} Supreme Court hits")
            for r in results[q]:
                if len(have) >= cap:
                    break
                case_no = r["사건번호"].split(",")[0].strip()
                if case_no in have or r["판례일련번호"] in known:
                    continue
                xml = service_xml("prec", ID=r["판례일련번호"])
                root = ET.fromstring(xml)
                if not root.findtext("사건번호"):
                    print(f"  {r['판례일련번호']}: not found", file=sys.stderr)
                    continue
                (OUT / f"{root.findtext('사건번호')}.xml").write_bytes(xml)
                have.add(case_no)
                known.add(r["판례일련번호"])
                manifest["cases"].append(_entry(root, q))
                time.sleep(0.5)
        if len(have) >= cap:
            return


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--since", default="20100101", help="YYYYMMDD lower bound on decision date")
    f = sub.add_parser("fetch")
    f.add_argument("ids", nargs="+", help="판례일련번호 values from `search`")
    b = sub.add_parser("bulk")
    b.add_argument("--since", default="20100101")
    b.add_argument("--max", type=int, default=400, help="stop once this many cases are on disk")
    args = p.parse_args()
    if args.cmd == "search":
        cmd_search(args.query, args.since)
    elif args.cmd == "bulk":
        cmd_bulk(args.since, args.max)
    else:
        cmd_fetch(args.ids)


if __name__ == "__main__":
    main()
