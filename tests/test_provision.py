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
    assert "근로기준법#11" in nodes["근로기준법 시행령#7의2"]["parent_provisions"]
    assert "근로기준법 시행령#7의2" in nodes["근로기준법#11"]["implementing_provisions"]


def test_same_law_reference_and_reverse_link(nodes):
    # 제18조③ "…제55조와 제60조를 적용하지 아니한다" — an exclusion of both articles.
    assert {"근로기준법#55", "근로기준법#60"} <= set(nodes["근로기준법#18"]["references"])
    for target in ("근로기준법#55", "근로기준법#60"):
        assert "근로기준법#18" in nodes[target]["referenced_by"]
        assert nodes[target]["referenced_by_cues"]["근로기준법#18"] == "exception"


def test_delegation_is_not_a_same_law_reference(nodes):
    # 시행령 "법 제11조제2항" points at the parent law: a delegation link, not a 시행령 제11조 reference.
    assert "근로기준법 시행령#11" not in nodes["근로기준법 시행령#7"]["references"]
    assert "근로기준법#11" in nodes["근로기준법 시행령#7"]["parent_provisions"]


def test_quoted_other_law_is_not_a_same_law_reference(nodes):
    # 파견법 제8조 3호 "「근로기준법」 제7조, 제9조, 제20조부터 제22조까지 …" — those belong to 근로기준법.
    refs = set(nodes["파견근로자 보호 등에 관한 법률#8"]["references"])
    assert not refs & {f"파견근로자 보호 등에 관한 법률#{n}" for n in (9, 20, 21, 22, 36, 46)}
    assert "파견근로자 보호 등에 관한 법률#7" in refs  # the bare "제7조에 따른 근로자파견사업" is this law
    # 「…」(이하 "고용산재보험료징수법"이라 한다) 제3조 … — an abbreviated other law.
    assert nodes["임금채권보장법#4"]["references"] == []


def test_reference_range_expands():
    from app.ingest.provision import _same_law_refs
    assert _same_law_refs("제55조부터 제57조까지의 규정") == ["55", "56", "57"]
    assert _same_law_refs("「민법」 제3조 및 제5조와 제9조") == []
