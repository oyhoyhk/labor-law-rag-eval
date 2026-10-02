"""참조조문 parsing and precedent expansion — no LLM, no index."""

import hashlib

import pytest

import app.rag as rag
from app.ingest.precedent import Precedent, ref_article_ids
from app.rag import (PROMPT_VERSION, PROMPT_VERSION_PRECEDENT, SYSTEM, SYSTEM_PARTIAL, Block, Options, _render,
                     finalize)

CORPUS = {"근로기준법#2", "근로기준법#17", "근로기준법#30", "근로기준법#60", "근로기준법 시행령#6",
          "파견근로자 보호 등에 관한 법률#6의2", "남녀고용평등과 일ㆍ가정 양립 지원에 관한 법률#19"}


@pytest.mark.parametrize("ref, expected", [
    ("근로기준법 제2조 제1항 제5호, 제17조, 근로기준법 시행령 제6조",
     ["근로기준법#2", "근로기준법#17", "근로기준법 시행령#6"]),
    ("파견근로자 보호 등에 관한 법률 제6조의2 제1항, 제2항", ["파견근로자 보호 등에 관한 법률#6의2"]),
    ("[1] 근로기준법 제60조 / [2] 민법 제2조, 제17조", ["근로기준법#60"]),  # 민법 resets the carried-over law
    ("남녀고용평등과 일·가정 양립 지원에 관한 법률 제19조 제1항", ["남녀고용평등과 일ㆍ가정 양립 지원에 관한 법률#19"]),
    ("파견근로자보호 등에 관한 법률 제6조의2", ["파견근로자 보호 등에 관한 법률#6의2"]),  # spacing variant
    ("구 근로기준법(2017. 11. 28. 법률 제15108호로 개정되기 전의 것) 제2조, 제17조(현행 제30조 참조)",
     ["근로기준법#2", "근로기준법#17"]),
    ("구 근로기준법(2007. 4. 11. 법률 제8372호로 전부 개정되기 전의 것) 제30조, 근로기준법 제60조",
     ["근로기준법#60"]),  # numbering differs before a full rewrite
    ("근로기준법 제2조, 제2조 제1항, 제99조", ["근로기준법#2"]),  # dedup; articles outside the corpus dropped
])
def test_ref_article_ids(ref, expected):
    assert ref_article_ids(ref, CORPUS) == expected


def test_legacy_prompts_unchanged():
    assert hashlib.sha256(SYSTEM.encode()).hexdigest()[:16] == "a410814ef12c4f72"
    assert hashlib.sha256(SYSTEM_PARTIAL.encode()).hexdigest()[:16] == "be8436aaccf9eff0"
    assert Options(precedents=False).prompt == PROMPT_VERSION
    assert Options().precedents and Options().prompt == PROMPT_VERSION_PRECEDENT  # default since 2026-10-03


class FakeScorer:
    def __init__(self, scores):
        self._scores = scores

    def scores(self, query, ids):
        return {p: self._scores[p] for p in ids if p in self._scores}


def _prec(pid, holding="근로자에 해당한다고 보아야 한다."):
    return Precedent(id=f"판례#{pid}", case_no=pid, decided="2024-12-19", title="임금", ref_articles="",
                     issues="[1] 근로자성 판단 기준", holding=holding, holding_from_reasons=False)


@pytest.fixture
def fake(monkeypatch):
    nodes = {"근로기준법#2": {"precedents": ["판례#A", "판례#B"]},
             "근로기준법#60": {"precedents": ["판례#B", "판례#C", "판례#D"]},
             "근로기준법 시행령#6": {"precedents": ["판례#E"]}}
    scores = {"판례#A": 0.60, "판례#B": 0.70, "판례#C": 0.80, "판례#D": 0.40, "판례#E": 0.99}
    precs = {f"판례#{k}": _prec(k) for k in "ABCDE"}
    monkeypatch.setattr(rag, "graph", lambda: nodes)
    monkeypatch.setattr(rag, "precedent_scorer", lambda: FakeScorer(scores))
    monkeypatch.setattr(rag, "precedents", lambda: precs)
    return precs


def _hits():
    return [Block("S1", "c1", ["근로기준법#2"], "제2조(정의)", 0.7),
            Block("S2", "c2", ["근로기준법#60"], "제60조(연차 유급휴가)", 0.6),
            Block("S3", "art:근로기준법 시행령#6", ["근로기준법 시행령#6"], "제6조", 0.0, linked=True, via="link")]


def test_precedent_expansion_uses_search_hits_only(fake):
    cands = rag.precedent_candidates("질문", _hits())
    assert [c[0] for c in cands] == ["판례#C", "판례#B", "판례#A", "판례#D"]  # 판례#E hangs off a linked block
    assert dict((c[0], c[2]) for c in cands)["판례#B"] == ["근로기준법#2", "근로기준법#60"]


def test_precedent_blocks_threshold_and_cap(fake, monkeypatch):
    blocks = rag._precedent_blocks("질문", _hits(), 3)
    assert [(b.source, b.article_ids, b.via, b.linked) for b in blocks] == [
        ("S4", ["판례#C"], "precedent", True), ("S5", ["판례#B"], "precedent", True)]
    assert blocks[0].text == fake["판례#C"].render()
    monkeypatch.setattr(rag, "PREC_TAU", 0.75)
    assert [b.article_ids for b in rag._precedent_blocks("질문", _hits(), 3)] == [["판례#C"]]


def test_long_holding_truncated_at_sentence_issues_kept(fake, monkeypatch):
    fake["판례#C"] = _prec("C", "가" * 10 + "다. " + "나" * 50 + "다.")
    monkeypatch.setattr(rag, "PREC_HOLDING_CHARS", 30)
    b = rag._precedent_blocks("질문", _hits(), 3)[0]
    assert b.text.endswith("가" * 10 + "다. …(이하 생략)") and "[1] 근로자성 판단 기준" in b.text


def test_precedent_render_and_citation(fake):
    b = rag._precedent_blocks("질문", _hits(), 3)[0]
    assert _render(b, "2026-10-01", True).startswith("[S4] (검색된 조문 근로기준법 제60조에 연결된 대법원 판례)\n[판례]")
    s1 = _hits()[0]
    s1.status = {"status": "in_force", "notes": []}
    text = "제2조가 근로자를 정의합니다.[S1]\n대법원은 근로자에 해당한다고 판단했습니다.[S4]"
    status, cits, _ = finalize(text, [s1, b])
    assert status == "answered"
    statute, prec = cits
    assert statute["source_type"] == "statute" and statute["status"] == "in_force"
    assert prec["source_type"] == "precedent" and prec["article_ids"] == ["판례#C"]
    assert prec["article"] == "대법원 2024. 12. 19. 선고 C 판결" and prec["status"] == "not_applicable"
    assert "근로자에 해당한다" in prec["quote"]


def test_expansion_off_when_disabled(monkeypatch):
    monkeypatch.setattr(rag, "retriever", lambda s: type("R", (), {"search": lambda self, q, k: []})())
    monkeypatch.setattr(rag, "precedent_scorer", lambda: pytest.fail("precedent index touched with the flag off"))
    assert rag.build_blocks("질문", Options(precedents=False), "2026-10-01") == []
