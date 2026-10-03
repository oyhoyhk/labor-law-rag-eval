"""Build the Part C comparison page: baseline v2 (GT v2.1, 100 items) vs each experiment, with noise floor, CI and per-item changes.

Usage: uv run python tools/build_experiment_compare_page.py OUT.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "eval/results/v2"

# Mean generation input tokens per call. Measured from run predictions where they survive (runs/ is local);
# siblings / reverse-refs come from their findings docs (worktree runs were removed after merge).
EXPERIMENTS = [
    {"key": "v2-final", "name": "최종 구성", "flag": "기본값 (조 전체 색인 + 판례)", "tokens": 6075,
     "hypothesis": "조 전체 색인과 판례 연결을 함께 쓰면 분할·판례 유형이 함께 개선될 것", "decision": "채택", "tone": "keep"},
    {"key": "v2-precedents", "name": "H7 판례 연결", "flag": "--precedents", "tokens": 5581,
     "cost": 485.36,  # run hit the 400원 cap at 81/100 (426.71원) and was resumed from cache (58.65원)
     "hypothesis": "조문에 연결된 대법원 판례를 주입하면 판례형 완전 정답이 오를 것", "decision": "채택", "tone": "keep"},
    {"key": "v2-h4-no-inject", "name": "H4 시행 상태 주입 끄기", "flag": "--no-inject", "tokens": 3253,
     "hypothesis": "시행 상태 헤더를 빼면 시점형 완전 정답이 떨어질 것", "decision": "가설 지지, 주입 유지", "tone": "keep"},
    {"key": "v2-h1-fixed", "name": "H1 고정 길이 512토큰", "flag": "--strategy fixed", "tokens": 5817,
     "hypothesis": "고정 길이 분할은 과잉 거절을 늘리고 인용 정밀도를 떨어뜨릴 것", "decision": "기각, 조 단위 유지", "tone": "reject"},
    {"key": "v2-k10", "name": "k 5 → 10", "flag": "--k 10", "tokens": 5640,
     "hypothesis": "검색 폭 확대로 Recall(all)이 오르고 답변은 노이즈 내일 것", "decision": "검색 개선 확정, 답변 미확인", "tone": "mixed"},
    {"key": "v2-siblings", "name": "형제 청크 동반", "flag": "--siblings", "tokens": 4179,
     "hypothesis": "분할된 조의 나머지 조각을 주면 분할형 완전 정답이 오를 것", "decision": "방향 일치, 효과 미확인", "tone": "candidate"},
    {"key": "v2-reverse-refs", "name": "조문 역참조 확장", "flag": "--reverse-refs", "tokens": 3785,
     "hypothesis": "예외 조항을 참조하는 조문을 붙이면 예외형 완전 정답이 오를 것", "decision": "방향 일치, 효과 미확인", "tone": "candidate"},
    {"key": "v2-partial-prompt", "name": "부분 답변 프롬프트", "flag": "--prompt gen-v2-partial", "tokens": 3807,
     "hypothesis": "효과 없음 예측(1차에서 대상 미해결)", "decision": "미채택, 범위 밖 거절 악화", "tone": "reject"},
]
BASE_TOKENS = 3576
# Context-building pipeline: each step's baseline value, and what each experiment changed (others = baseline).
STEPS = [
    ("index", "① 색인 단위", "법령을 어떤 크기로 잘라 검색 대상으로 만드나"),
    ("k", "② 검색 개수", "질문과 비슷한 조문을 몇 개 가져오나"),
    ("links", "③ 위임 연결", "검색된 조와 연결된 시행령·상위법을 붙이나"),
    ("siblings", "④ 나머지 조각", "쪼개진 조의 다른 조각을 함께 붙이나"),
    ("reverse", "⑤ 예외 조문", "검색된 조를 '예외'로 가리키는 조문을 붙이나"),
    ("precedents", "⑥ 판례", "검색된 조에 연결된 대법원 판례를 붙이나"),
    ("status", "⑦ 시행 상태 표시", "조문마다 '시행 중·시행 예정·효력 상실'을 표시하나"),
    ("prompt", "⑧ 답변 지시", "LLM에게 어떤 규칙으로 답하라고 하나"),
]
BASE_CFG = {"index": "조 단위 (긴 조는 항·호에서 분할)", "k": "5개", "links": "켬 (최대 3개)", "siblings": "끔",
            "reverse": "끔", "precedents": "끔", "status": "켬", "prompt": "근거 블록만으로 답, 없으면 거절"}
CHANGES = {
    "v2-final": {"index": "조 전체 (분할 없음)", "precedents": "켬 (유사도 0.54 이상 최대 2건)",
                 "prompt": "조문 → 대법원 판단 → 사안별 차이 단서"},
    "v2-precedents": {"precedents": "켬 (유사도 0.54 이상 최대 2건)", "prompt": "조문 → 대법원 판단 → 사안별 차이 단서"},
    "v2-h4-no-inject": {"status": "끔"},
    "v2-h1-fixed": {"index": "고정 길이 512토큰 (조 경계 무시)"},
    "v2-k10": {"k": "10개"},
    "v2-siblings": {"siblings": "켬 (최대 4개)"},
    "v2-reverse-refs": {"reverse": "켬 (최대 2개)"},
    "v2-partial-prompt": {"prompt": "근거가 일부만 있어도 확인된 만큼 답"},
}

# Plain-language summary shown first on the page: what changed, what happened, and which item type it targeted.
PLAIN = {
    "v2-final": ("조를 통째로 색인하고, 조문에 연결된 대법원 판례도 함께 제공 (현재 기본값)",
                 "판례가 필요한 질문 9개 중 4개를 새로 맞힘. 전체로도 올랐지만 우연과 구별이 아슬아슬함. 대신 정답 목록 밖 근거 인용이 늘어남",
                 "precedent", "개선 시도"),
    "v2-k10": ("검색해 오는 조문 수를 5개에서 10개로 늘림",
               "정답 조문을 더 많이 찾아 전체 정답률이 확실히 오름(우연 아님). 대신 입력이 길어져 질문당 비용 약 1.6배",
               None, "개선 시도"),
    "v2-precedents": ("조문에 연결된 대법원 판례를 함께 제공",
                      "판례가 필요한 질문 9개 중 4개 해결(우연 아님). 전체 정답률 상승은 판단 보류",
                      "precedent", "개선 시도"),
    "v2-siblings": ("긴 조가 여러 조각으로 나뉘었을 때 나머지 조각도 함께 제공",
                    "노린 유형 12문항 중 2문항 개선. 문항이 적어 우연과 구별 안 됨",
                    "split", "개선 시도"),
    "v2-reverse-refs": ("검색된 조문을 '예외'로 가리키는 다른 조문도 함께 제공",
                        "노린 유형 12문항 중 2문항 개선, 다른 2문항 하락. 판단 보류",
                        "exception", "개선 시도"),
    "v2-partial-prompt": ("근거가 일부만 있어도 아는 만큼 답하도록 지시",
                          "효과 없음. 오히려 답하면 안 되는 질문 1개에 답해 버림",
                          None, "개선 시도"),
    "v2-h1-fixed": ("조 단위가 아니라 512토큰씩 기계적으로 잘라 색인 (나빠지는지 확인하는 실험)",
                    "거절이 늘고 인용 정확도가 절반으로 떨어짐 → 조 단위 색인이 맞다는 근거",
                    None, "확인 실험"),
    "v2-h4-no-inject": ("조문 앞의 '시행 예정·효력 상실' 표시를 빼 봄 (확인 실험)",
                        "시점을 묻는 질문 정답률 0.67 → 0.24로 급락 → 이 표시가 핵심 장치라는 근거",
                        "temporal", "확인 실험"),
}
LEVELS = ["L1", "L2", "L3", "L4", "L5a", "L5b", "OOS", "SUM"]
TAGS = ["exception", "split", "temporal", "delegation", "precedent"]
LEVEL_METRICS = ["M1_recall_any", "M3_citation_precision", "M4_kp_coverage", "M5_unsupported_rate"]


def jl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open()]


gold = {g["id"]: g for g in jl(ROOT / "eval/gold/gold_v2.jsonl")}
noise = json.loads((ROOT / "eval/results/noise_floor.json").read_text())["metrics"]
base_scores = {s["id"]: s for s in jl(RES / "baseline-v2/scores.jsonl")}
base_report = json.loads((RES / "baseline-v2/report.json").read_text())


def levels(report: dict) -> dict:
    return {lv: {m: report["by_level"].get(lv, {}).get(m, [None])[0] for m in LEVEL_METRICS} for lv in LEVELS}


def item_changes(exp_scores: dict) -> list[dict]:
    out = []
    for i, b in base_scores.items():
        e = exp_scores[i]
        bk, ek = b.get("m4_kp_coverage"), e.get("m4_kp_coverage")
        status_changed = b["status"] != e["status"]
        if status_changed or (bk is not None and ek is not None and abs(ek - bk) > 1e-9):
            out.append({"id": i, "level": b["level"], "q": gold[i]["question"],
                        "base_status": b["status"], "exp_status": e["status"], "base_kp": bk, "exp_kp": ek,
                        "base_m6": b.get("m6_temporal_error"), "exp_m6": e.get("m6_temporal_error")})
    return sorted(out, key=lambda r: ((r["exp_kp"] or 0) - (r["base_kp"] or 0), r["id"]))


# Baseline = per-item mean of the three identical-config runs; an item counts as gained/lost against that mean.
BASE_RUNS = ["baseline-v2", "noise-v2-2", "noise-v2-3"]
base_m0 = {}
for k in BASE_RUNS:
    for s in jl(RES / k / "scores.jsonl"):
        base_m0.setdefault(s["id"], []).append(float(bool(s.get("m0_correct"))))
base_m0 = {i: sum(v) / len(v) for i, v in base_m0.items()}


def flips(exp_scores: dict) -> dict:
    up = sum(1 for i, b in base_m0.items() if b < 0.5 and exp_scores[i].get("m0_correct"))
    down = sum(1 for i, b in base_m0.items() if b >= 0.5 and not exp_scores[i].get("m0_correct"))
    return {"up": up, "down": down}


exps = []
for x in EXPERIMENTS:
    d = RES / x["key"]
    manifest = json.loads((d / "manifest.json").read_text())
    diff = json.loads((d / "diff_vs_base.json").read_text())
    what, result, target, kind = PLAIN[x["key"]]
    exps.append({**x, "what": what, "result": result, "target": target, "kind": kind,
                 "cfg": {**BASE_CFG, **CHANGES[x["key"]]},
                 "flips": flips({s["id"]: s for s in jl(d / "scores.jsonl")}),
                 "cost": x.get("cost", manifest["cost_krw"]), "rows": diff["rows"],
                 "subsets": [r for r in diff["subsets"] if r["field"] == "complete"],
                 "levels": levels(json.loads((d / "report.json").read_text())),
                 "changes": item_changes({s["id"]: s for s in jl(d / "scores.jsonl")})})

noise_sub = json.loads((ROOT / "eval/results/noise_floor.json").read_text()).get("subsets", {})
data = {"steps": [{"key": k, "name": n, "desc": d} for k, n, d in STEPS], "base_cfg": BASE_CFG, "noise": {k: v["range"] for k, v in noise.items()}, "base_tokens": BASE_TOKENS, "tags": TAGS,
        "tag_noise": {t: noise_sub.get(f"{t}:complete", {}).get("range") for t in TAGS},
        "base_levels": levels(base_report), "level_n": {lv: base_report["by_level"].get(lv, {}).get("n", 0) for lv in LEVELS},
        "experiments": exps}
page = (ROOT / "tools/experiment_compare_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(exps)} experiments → {sys.argv[1]}")
