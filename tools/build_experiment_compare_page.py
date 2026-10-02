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


exps = []
for x in EXPERIMENTS:
    d = RES / x["key"]
    manifest = json.loads((d / "manifest.json").read_text())
    diff = json.loads((d / "diff_vs_base.json").read_text())
    exps.append({**x, "cost": x.get("cost", manifest["cost_krw"]), "rows": diff["rows"],
                 "subsets": [r for r in diff["subsets"] if r["field"] == "complete"],
                 "levels": levels(json.loads((d / "report.json").read_text())),
                 "changes": item_changes({s["id"]: s for s in jl(d / "scores.jsonl")})})

noise_sub = json.loads((ROOT / "eval/results/noise_floor.json").read_text()).get("subsets", {})
data = {"noise": {k: v["range"] for k, v in noise.items()}, "base_tokens": BASE_TOKENS, "tags": TAGS,
        "tag_noise": {t: noise_sub.get(f"{t}:complete", {}).get("range") for t in TAGS},
        "base_levels": levels(base_report), "level_n": {lv: base_report["by_level"].get(lv, {}).get("n", 0) for lv in LEVELS},
        "experiments": exps}
page = (ROOT / "tools/experiment_compare_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(exps)} experiments → {sys.argv[1]}")
