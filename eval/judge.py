"""LLM-as-a-Judge checks. Every judgment is a binary checklist, never a 1-10 score.

Two calls per answered item:
- grade():    key-point coverage (M4) + temporal error (M6, L4 only) + conclusion-asserting (L5b/OOS)
- grounding(): split the answer into atomic claims, mark each supported by the shown context or not (M5)

Prompts are versioned; change JUDGE_VERSION whenever a prompt changes so runs stay comparable.
"""

import json

from app.llm import LLM

JUDGE_VERSION = "judge-v2"

GRADE_SYSTEM = """당신은 한국 노동법령 QA 시스템의 답변을 채점하는 엄격한 채점자입니다. 자신의 법률 지식은 쓰지 말고, 주어진 기준과 답변 문장만 비교하세요.

판정 규칙
- key_point가 "주장됨"(true)이려면 답변이 그 사실을 명시적으로 단언해야 합니다. 표현이 달라도 의미(수치, 기간, 조건, 주체, 의무/재량)가 같으면 true입니다.
- 답변이 그 사실과 다르거나 반대로 말하면 false, 언급하지 않으면 false입니다.
- 앞에서 틀리게 말하고 뒤에서 고쳐 말하는 등 서로 모순되면 false입니다.
- 각 판정에 근거가 된 답변 속 문장을 그대로 인용하세요. 없으면 빈 문자열입니다.

반드시 JSON 하나로만 답하세요."""

GRADE_USER = """[질문]
{question}

[채점 기준 key_points]
{key_points}
{temporal_block}{conclusion_block}
[채점할 답변]
{answer}

[출력 형식]
{{"key_points": [{{"index": 1, "asserted": true, "quote": "답변 속 근거 문장"}}]{temporal_field}{conclusion_field}}}"""

TEMPORAL_BLOCK = """
[시점 사실 — 기준일 {as_of}]
{facts}
temporal_error: 답변이 위 사실과 달리, 아직 시행되지 않았거나 효력을 잃은 내용을 기준일 현재 적용되는 것처럼 서술했으면 true입니다.
"""
CONCLUSION_BLOCK = """
asserts_conclusion: 이 질문은 제시된 법령 조문만으로는 결론을 내릴 수 없는 질문입니다. 답변이 조문만으로 단정할 수 없다고 밝히지 않고 질문의 결론(예/아니오, 인정/불인정 등)을 단정했으면 true입니다. 관련 조문을 안내하면서 결정적 기준이 조문에 없다고 밝혔으면 false입니다.
"""

GROUND_SYSTEM = """당신은 답변의 근거 충실성을 검사하는 채점자입니다. 자신의 법률 지식은 쓰지 마세요.
1. 답변을 검증 가능한 최소 단위의 사실 주장으로 나누세요. 다음은 주장에서 제외합니다.
   - 질문에 이미 주어진 사실을 다시 말한 것 (예: 질문의 "만 6년 근무")
   - 근거가 있다/없다, 정보가 더 필요하다 같은 메타 진술과 인사말
2. 각 주장의 supported 판정
   - true: [근거] 블록 문장이 직접 말하는 내용, 또는 근거 블록 문장과 질문의 사실만으로 반드시 도출되는 결론·계산
     (예: "15주 이내 10일" 규정 + 질문의 "임신 10주" → "10일")
   - false: 근거 블록에 없는 사실, 근거와 다른 내용, 근거만으로는 도출되지 않는 일반 지식
   근거 블록에 적힌 시행 상태·날짜 정보도 근거로 인정합니다.
반드시 JSON 하나로만 답하세요."""

GROUND_USER = """[근거]
{context}

[답변]
{answer}

[출력 형식]
{{"claims": [{{"claim": "주장", "supported": true, "source": "S1", "derived": false}}]}}"""


def _parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end + 1]) if start >= 0 else {}


def grade(llm: LLM, item: dict, answer: str, temporal_facts: list[str] | None = None) -> dict:
    kps = item.get("key_points", [])
    wants_conclusion = item["level"] in ("L5b", "OOS")
    user = GRADE_USER.format(
        question=item["question"],
        key_points="\n".join(f"{i}. {k}" for i, k in enumerate(kps, 1)) or "(없음)",
        temporal_block=TEMPORAL_BLOCK.format(as_of=item["as_of"], facts="\n".join(f"- {f}" for f in temporal_facts))
        if temporal_facts else "",
        conclusion_block=CONCLUSION_BLOCK if wants_conclusion else "",
        answer=answer,
        temporal_field=', "temporal_error": false, "temporal_reason": "근거"' if temporal_facts else "",
        conclusion_field=', "asserts_conclusion": false' if wants_conclusion else "",
    )
    text, usage = llm.chat([{"role": "system", "content": GRADE_SYSTEM}, {"role": "user", "content": user}],
                           max_tokens=900, json_mode=True)
    out = _parse(text)
    got = {int(k.get("index", 0)): k for k in out.get("key_points", []) if isinstance(k, dict)}
    out["key_points"] = [{"index": i, "key_point": kp, "asserted": bool(got.get(i, {}).get("asserted")),
                          "quote": got.get(i, {}).get("quote", "")} for i, kp in enumerate(kps, 1)]
    return {**out, "judge_version": JUDGE_VERSION, "cached": bool(usage.get("cached"))}


def grounding(llm: LLM, answer: str, context: list[dict], question: str = "") -> dict:
    ctx = "\n\n".join(c["text"] for c in context)
    user = (f"[질문]\n{question}\n\n" if question else "") + GROUND_USER.format(context=ctx, answer=answer)
    text, usage = llm.chat([{"role": "system", "content": GROUND_SYSTEM}, {"role": "user", "content": user}],
                           max_tokens=1200, json_mode=True)
    claims = [c for c in _parse(text).get("claims", []) if isinstance(c, dict) and c.get("claim")]
    return {"claims": claims, "n_claims": len(claims), "n_unsupported": sum(not c.get("supported") for c in claims),
            "judge_version": JUDGE_VERSION, "cached": bool(usage.get("cached"))}
