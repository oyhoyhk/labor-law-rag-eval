"""Build the Part C comparison page: baseline v1.1 vs each experiment, with noise floor, CI and per-item changes.

Usage: uv run python tools/build_experiment_compare_page.py OUT.html
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "eval/results"

# Mean generation input tokens per call. Measured from run predictions where they survive (runs/ is local);
# siblings / reverse-refs come from their findings docs (worktree runs were removed after merge).
EXPERIMENTS = [
    {"key": "exp_h4_no_inject", "name": "H4 시행 상태 주입 끄기", "flag": "--no-inject", "tokens": 3396,
     "hypothesis": "시행 상태 헤더를 빼면 시점 오류가 늘 것", "decision": "가설 지지, 주입 유지", "tone": "keep"},
    {"key": "exp_h1_fixed", "name": "H1 고정 길이 512토큰", "flag": "--strategy fixed", "tokens": 5756,
     "hypothesis": "고정 길이 분할은 조 단위보다 나쁠 것", "decision": "기각, 조 단위 유지", "tone": "reject"},
    {"key": "exp_k10", "name": "k 5 → 10", "flag": "--k 10", "tokens": 5854,
     "hypothesis": "검색 폭 확대로 밀려난 정답 조문 확보", "decision": "검색 개선 확정, 답변 개선 미확정", "tone": "mixed"},
    {"key": "exp_siblings", "name": "형제 청크 동반", "flag": "--siblings", "tokens": 4320,
     "hypothesis": "같은 조의 분할 조각을 함께 주면 누락 항이 줄 것", "decision": "이 형태로는 미채택", "tone": "reject"},
    {"key": "exp_reverse_refs", "name": "조문 역참조 확장", "flag": "--reverse-refs", "tokens": 3902,
     "hypothesis": "예외 조항을 참조하는 조문을 붙이면 예외 누락이 줄 것", "decision": "유지 후보(저비용·저소음)", "tone": "candidate"},
    {"key": "exp_partial_prompt", "name": "부분 답변 프롬프트", "flag": "--prompt gen-v2-partial", "tokens": None,
     "hypothesis": "근거가 일부만 있으면 확인된 부분만 답하게 하면 정답 포인트가 오를 것", "decision": "미채택", "tone": "reject"},
]
BASE_TOKENS = 3701
LEVELS = ["L1", "L2", "L3", "L4", "L5a", "L5b", "OOS", "SUM"]
LEVEL_METRICS = ["M1_recall_any", "M3_citation_precision", "M4_kp_coverage", "M5_unsupported_rate"]


def jl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open()]


gold = {g["id"]: g for g in jl(ROOT / "eval/gold/gold_v1_1.jsonl")}
noise = json.loads((RES / "noise_floor.json").read_text())["metrics"]
base_scores = {s["id"]: s for s in jl(RES / "baseline_v1_1/scores.jsonl")}
base_report = json.loads((RES / "baseline_v1_1/report.json").read_text())


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
    exps.append({**x, "cost": manifest["cost_krw"], "rows": json.loads((d / "diff_vs_base.json").read_text())["rows"],
                 "levels": levels(json.loads((d / "report.json").read_text())),
                 "changes": item_changes({s["id"]: s for s in jl(d / "scores.jsonl")})})

data = {"noise": {k: v["range"] for k, v in noise.items()}, "base_tokens": BASE_TOKENS,
        "base_levels": levels(base_report), "level_n": {lv: base_report["by_level"].get(lv, {}).get("n", 0) for lv in LEVELS},
        "experiments": exps}
page = (ROOT / "tools/experiment_compare_page.html").read_text()
Path(sys.argv[1]).write_text(page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
print(f"{len(exps)} experiments → {sys.argv[1]}")
