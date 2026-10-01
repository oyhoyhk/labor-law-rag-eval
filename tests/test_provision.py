"""Provision-graph expectations pinned to official law.go.kr effective dates."""

import json

import pytest

from app.ingest.provision import GRAPH, build, status_at

AS_OF = "2026-10-01"


@pytest.fixture(scope="module")
def nodes():
    return (json.loads(GRAPH.read_text()) if GRAPH.exists() else build())["nodes"]


@pytest.mark.parametrize("aid, effective, promulgated", [
    ("근로기준법#54", "2026-12-10", "2026-06-09"),  # 공포 후 6개월 경과
    ("근로기준법#60", "2027-06-10", "2026-06-09"),  # 공포 후 1년 경과
    ("근로기준법#105", "2026-10-02", "2026-08-04"),  # 형사소송법 타법개정
])
def test_scheduled_change_dates(nodes, aid, effective, promulgated):
    assert any(p["effective"] == effective and p["promulgated"] == promulgated for p in nodes[aid]["pending"])


def test_hourly_annual_leave_is_pending_not_current(nodes):
    change = next(p for p in nodes["근로기준법#60"]["pending"] if p["effective"] == "2027-06-10")
    assert any("시간단위" in t for t in change["changed_paragraphs"])
    assert status_at(nodes["근로기준법#60"], AS_OF)["status"] == "amendment_pending"
    assert status_at(nodes["근로기준법#60"], "2027-06-10")["status"] == "in_force"


def test_expired_special_overtime_paragraphs(nodes):
    st = status_at(nodes["근로기준법#53"], AS_OF)
    assert st["status"] == "partially_expired"
    assert "③·⑥" in st["notes"][0]


def test_expired_whole_article(nodes):
    assert status_at(nodes["근로기준법#16"], AS_OF)["status"] == "expired"


def test_untouched_article_is_in_force(nodes):
    assert status_at(nodes["근로기준법#50"], AS_OF) == {"status": "in_force", "notes": []}


def test_delegation_links_decree_to_statute(nodes):
    assert "근로기준법#11" in nodes["근로기준법 시행령#7의2"]["delegates_to"]
    assert "근로기준법 시행령#7의2" in nodes["근로기준법#11"]["delegated_from"]
