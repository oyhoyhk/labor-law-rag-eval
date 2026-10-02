"""BM25 bigram tokenization/scoring, RRF ordering, and flag-off invariance — no model, no index."""

from app.hybrid import BM25, rrf, tokenize
from app.rag import (FEWSHOT_SUFFIX, PROMPT_VERSION_PRECEDENT, SYSTEM_PRECEDENT, SYSTEMS, Block, Options, messages)


def test_tokenize_bigrams_per_token():
    assert tokenize("통상임금을 산정") == ["통상", "상임", "임금", "금을", "산정"]
    assert tokenize("제74조(출산전후휴가)") == ["제7", "74", "4조", "출산", "산전", "전후", "후휴", "휴가"]
    assert tokenize("법 , 및") == ["법", "및"]  # one-char tokens kept whole, punctuation-only tokens dropped


def test_bm25_prefers_term_match_and_rarer_terms():
    docs = ["연차 유급휴가는 1년간 80퍼센트 이상 출근한 근로자에게 준다",
            "통상임금은 정기적 일률적으로 지급하는 임금이다",
            "근로자에게 임금을 지급한다"]
    bm = BM25(docs)
    assert bm.top("통상임금", 3)[0] == 1
    assert bm.top("연차휴가", 1) == [0]
    assert 2 not in bm.scores("유급휴가")  # no shared bigram → not scored
    assert bm.idf["통상"] > bm.idf["근로"]  # appears in 1 doc vs 2


def test_bm25_length_normalisation():
    short, long_ = "퇴직금 지급", "퇴직금 지급 " + " ".join(f"기타{i}" for i in range(50))
    s = BM25([short, long_]).scores("퇴직금")
    assert s[0] > s[1]


def test_rrf_ordering_and_weights():
    dense, sparse = [1, 2, 3], [3, 4, 5]
    fused = rrf([dense, sparse], [1.0, 1.0], k=60)
    assert [i for i, _ in fused] == [3, 1, 2, 4, 5]  # in both lists beats either single list; 2·4 tie → id
    assert abs(fused[0][1] - (1 / 63 + 1 / 61)) < 1e-12
    # A tiny BM25 weight leaves the dense order intact.
    assert [i for i, _ in rrf([dense, sparse], [1.0, 0.01], k=60)][:3] == [1, 2, 3]
    assert [i for i, _ in rrf([[5], [6]], [1.0, 1.0], k=60)] == [5, 6]  # exact tie → smaller id first


def test_flags_off_keep_prompt_and_messages():
    opt = Options()
    assert not opt.fewshot_dev and not opt.hybrid and opt.prompt == PROMPT_VERSION_PRECEDENT
    b = Block("S1", "art:근로기준법#50", ["근로기준법#50"], "제50조(근로시간)\n③ 대기시간 등은 근로시간으로 본다.", 0.7)
    b.status = {"status": "in_force", "notes": []}
    msgs = messages("질문", [b], "2026-10-01", inject=True, prompt=opt.prompt)
    assert msgs[0]["content"] == SYSTEM_PRECEDENT.format(as_of="2026-10-01")
    assert "참고 예시" not in msgs[0]["content"] + msgs[1]["content"]


def test_fewshot_flag_uses_distinct_prompt_version():
    assert Options(fewshot_dev=True).prompt == "gen-v3-precedent+fewshot-dev"
    assert Options(fewshot_dev=True, precedents=False).prompt == "gen-v1" + FEWSHOT_SUFFIX
    assert all(not k.endswith(FEWSHOT_SUFFIX) for k in SYSTEMS)  # never a selectable base prompt
