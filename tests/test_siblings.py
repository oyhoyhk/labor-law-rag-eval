"""Sibling-chunk injection for split articles (no LLM; uses the local index and embedder)."""

import pytest

from app.rag import MAX_LINKED, MAX_SIBLINGS, Options, build_blocks

G021 = "우리 회사가 5인 이상 사업장인지 판단할 때 상시 근로자 수는 어떻게 계산하나요?"
PART2 = "art:근로기준법 시행령#7의2:2"
AS_OF = "2026-10-01"


@pytest.fixture(scope="module")
def blocks():
    return {on: build_blocks(G021, Options(strategy="article", top_k=5, include_siblings=on, precedents=False), AS_OF) for on in (False, True)}


def test_g021_part2_only_with_siblings(blocks):
    off, on = blocks[False], blocks[True]
    assert "art:근로기준법 시행령#7의2:1" in [b.chunk_id for b in off[:5]]
    assert PART2 not in [b.chunk_id for b in off]
    sib = [b for b in on if b.chunk_id == PART2]
    assert len(sib) == 1 and sib[0].via == "sibling" and sib[0].linked


def test_search_hits_unchanged_and_bounded(blocks):
    off, on = blocks[False], blocks[True]
    assert [b.chunk_id for b in on[:5]] == [b.chunk_id for b in off[:5]]  # M1 ranks unaffected
    assert [b.source for b in on] == [f"S{i + 1}" for i in range(len(on))]
    assert len({b.chunk_id for b in on}) == len(on)
    assert len(on) <= 5 + MAX_SIBLINGS + MAX_LINKED
