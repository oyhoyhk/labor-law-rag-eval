"""Prompt selection and answer classification — no LLM, no index."""

from app.rag import (PROMPT_VERSION, PROMPT_VERSION_PARTIAL, SYSTEM, SYSTEM_PARTIAL, Block, Options, finalize,
                     messages)


def _blocks() -> list[Block]:
    b = Block("S1", "art:근로기준법#50", ["근로기준법#50"], "제50조(근로시간)\n③ 대기시간 등은 근로시간으로 본다.", 0.7)
    b.status = {"status": "in_force", "notes": []}
    return [b]


def test_default_prompt_is_unchanged():
    assert Options().prompt == PROMPT_VERSION == "gen-v1"
    sys = messages("질문", [], "2026-10-01", inject=False)[0]["content"]
    assert sys == SYSTEM.format(as_of="2026-10-01")


def test_partial_option_selects_partial_prompt():
    opt = Options(prompt=PROMPT_VERSION_PARTIAL)
    sys = messages("질문", [], "2026-10-01", inject=False, prompt=opt.prompt)[0]["content"]
    assert sys == SYSTEM_PARTIAL.format(as_of="2026-10-01")
    assert "판단할 수 없다" in sys and "[정보 부족]" in sys and "2026-10-01" in sys


def test_finalize_refusal_first_line():
    status, cits, reason = finalize("[정보 부족]\n근거 블록에 관련 내용이 없습니다.", _blocks())
    assert (status, cits, reason) == ("insufficient_context", [], "model_declined")


def test_finalize_partial_answer_with_citation_is_answered():
    text = ("호출을 받아 실제로 일한 시간은 근로시간입니다. [S1]\n"
            "근거 블록만으로는 집에서 대기한 시간이 근로시간인지 판단할 수 없습니다.")
    status, cits, reason = finalize(text, _blocks())
    assert status == "answered" and reason is None
    assert [c["source"] for c in cits] == ["S1"]


def test_finalize_without_valid_citation_is_refusal():
    status, _, reason = finalize("근거 블록만으로는 판단할 수 없습니다. [S9]", _blocks())
    assert (status, reason) == ("insufficient_context", "no_valid_citation")
