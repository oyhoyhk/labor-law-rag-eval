"""Download the labor-law corpus snapshot.

For each statute we store the version in force today (현행) plus every scheduled
version (시행예정). The scheduled versions carry official effective dates, which the
provision graph uses instead of re-deriving dates from 부칙 text.

Usage: uv run python scripts/fetch_laws.py
"""

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lawapi import search, service_xml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "laws"
MANIFEST = ROOT / "data" / "manifest.json"

STATUTES = [
    "근로기준법",
    "최저임금법",
    "근로자퇴직급여 보장법",
    "남녀고용평등과 일ㆍ가정 양립 지원에 관한 법률",
    "기간제 및 단시간근로자 보호 등에 관한 법률",
    "파견근로자 보호 등에 관한 법률",
    "근로자참여 및 협력증진에 관한 법률",
    "임금채권보장법",
]
LEVELS = ["", " 시행령", " 시행규칙"]
KEEP = {"현행", "시행예정"}


def versions(name: str) -> list[dict]:
    """현행 + 시행예정 rows for an exact law name, one per (MST, 시행일자)."""
    rows = search("eflaw", name, nw="2,3")  # 2=시행예정, 3=현행
    seen, out = set(), []
    for r in rows:
        if r["법령명한글"] != name or r["현행연혁코드"] not in KEEP:
            continue
        key = (r["법령일련번호"], r["시행일자"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    if not any(r["현행연혁코드"] == "현행" for r in out):
        raise SystemExit(f"no 현행 version found for {name!r}")
    return sorted(out, key=lambda r: r["시행일자"])


def main() -> None:
    manifest = {"fetched_at": date.today().isoformat(), "source": "law.go.kr DRF eflaw", "documents": []}
    for statute in STATUTES:
        for level in LEVELS:
            name = statute + level
            law_dir = OUT / name
            law_dir.mkdir(parents=True, exist_ok=True)
            for v in versions(name):
                xml = service_xml("eflaw", MST=v["법령일련번호"], efYd=v["시행일자"])
                path = law_dir / f"{v['시행일자']}_{v['법령일련번호']}.xml"
                path.write_bytes(xml)
                manifest["documents"].append({
                    "name": name,
                    "law_id": v["법령ID"],
                    "mst": v["법령일련번호"],
                    "status": v["현행연혁코드"],
                    "promulgated": v["공포일자"],
                    "promulgation_no": v["공포번호"],
                    "effective": v["시행일자"],
                    "path": str(path.relative_to(ROOT)),
                    "sha256": hashlib.sha256(xml).hexdigest(),
                })
                print(f"{v['현행연혁코드']:4} {v['시행일자']} {name}")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    current = sum(d["status"] == "현행" for d in manifest["documents"])
    print(f"\n{current} current documents, {len(manifest['documents'])} versions total -> {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
