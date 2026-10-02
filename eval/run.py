"""Run the gold set through the RAG pipeline, judge the answers, and write a report.

Usage:
  uv run python -m eval.run --name baseline                 # all 56 items, judge on, cache on
  uv run python -m eval.run --name smoke --ids g001,g031,l5b02 --budget 50
  uv run python -m eval.run --name h4-off --no-inject       # H4 ablation
Outputs runs/<timestamp>_<name>/{predictions,judgments,scores}.jsonl, report.{json,md}, manifest.json
"""

import argparse
import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import date, datetime

from app.index import INDEX_DIR
from app.ingest.parse import ROOT
from app.llm import LLM, SEED, TEMPERATURE, BudgetExceeded
from app.rag import PROMPT_VERSION, Options, answer, graph, retriever
from app.ingest.provision import status_at
from eval import judge as J
from eval.metrics import aggregate, by_group, item_scores

GOLD = ROOT / "eval" / "gold" / "gold_v1.jsonl"
SPLITS = ROOT / "eval" / "gold" / "splits.json"
CACHE = ROOT / "data" / "cache" / "llm"
METRIC_KEYS = ["M1_recall_any", "M1_recall_all", "M1_mrr", "M2_oos_refusal", "M2_l5b_no_assertion", "M2_over_refusal", "M3_citation_precision", "M3_citation_recall", "M4_kp_coverage", "M4_all_kp",
               "M5_unsupported_rate", "M6_temporal_error"]


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def temporal_facts(item: dict) -> list[str]:
    facts = []
    for aid in item["gold_evidence"]:
        node = graph().get(aid)
        if node:
            st = status_at(node, item["as_of"])
            facts += [f"{aid}: {n}" for n in st["notes"]]
    return facts


def run_item(item: dict, opt: Options, gen: LLM, jdg: LLM | None) -> tuple[dict, dict | None]:
    pred = answer(item["question"], opt, date.fromisoformat(item["as_of"]), gen, include_context=True)
    pred = {"id": item["id"], **pred}
    if jdg is None or pred["status"] != "answered":
        return pred, None
    facts = temporal_facts(item) if item["level"] == "L4" else None
    j = {"id": item["id"], "grade": J.grade(jdg, item, pred["answer"], facts),
         "grounding": J.grounding(jdg, pred["answer"], pred["meta"]["context"] or [], item["question"])}
    return pred, j


def report_md(name: str, overall: dict, levels: dict, splits: dict, scores: list[dict], manifest: dict) -> str:
    def fmt(v):
        return "—" if v[0] is None else f"{v[0]:.3f} (n={v[1]})"
    lines = [f"# 평가 리포트: {name}", "",
             f"- 실행: {manifest['started_at']} · git `{manifest['git_sha']}`{' (dirty)' if manifest['git_dirty'] else ''}",
             f"- 설정: {json.dumps(manifest['config'], ensure_ascii=False)}",
             f"- 모델: {manifest['model']} · seed {SEED} · temperature {TEMPERATURE} · 임베딩 {manifest['embedding']}",
             f"- 비용: 생성+Judge {manifest['cost_krw']}원 · LLM 호출 {manifest['usage']['calls']}회 · 캐시 적중 {manifest['usage']['cache_hits']}회",
             "", "## 전체", "", "| 지표 | 값 |", "|---|---|"]
    lines += [f"| {k} | {fmt(overall[k])} |" for k in METRIC_KEYS]
    for title, groups in (("단계별", levels), ("분할별", splits)):
        cols = list(groups)
        lines += ["", f"## {title}", "", "| 지표 | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
        lines += [f"| {k} | " + " | ".join("—" if groups[c][k][0] is None else f"{groups[c][k][0]:.2f}" for c in cols) + " |"
                  for k in METRIC_KEYS]
    fails = [s for s in scores if not s["m2_correct_status"] or s.get("m1_recall_any") is False
             or (s.get("m4_kp_coverage") is not None and s["m4_kp_coverage"] < 1) or s.get("m6_temporal_error")
             or (s.get("m5_unsupported_rate") or 0) > 0]
    lines += ["", f"## 확인이 필요한 문항 ({len(fails)})", "", "| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |",
              "|---|---|---|---|---|---|---|"]
    for s in fails:
        lines.append(f"| {s['id']} | {s['level']} | {s['expected'][:3]}→{s['status'][:3]}"
                     f"{'(' + s['refusal_reason'] + ')' if s['refusal_reason'] else ''} | "
                     f"{'—' if s['m1_recall_any'] is None else ('O' if s['m1_recall_any'] else 'X')} | "
                     f"{'—' if s.get('m4_kp_coverage') is None else f'{s['m4_kp_coverage']:.2f}'} | "
                     f"{'—' if s.get('m5_unsupported_rate') is None else f'{s['m5_unsupported_rate']:.2f}'} | "
                     f"{'—' if 'm6_temporal_error' not in s else ('X' if s['m6_temporal_error'] else 'O')} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--strategy", default="article", choices=["article", "fixed"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--tau", type=float, default=Options.tau)
    ap.add_argument("--no-inject", action="store_true", help="H4 ablation: no effectivity headers")
    ap.add_argument("--no-links", action="store_true", help="disable delegation-link expansion")
    ap.add_argument("--split", default="all", choices=["all", "dev", "test"])
    ap.add_argument("--ids", default="")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--no-cache", action="store_true", help="force fresh LLM calls (noise-floor runs)")
    ap.add_argument("--judge-no-cache", action="store_true",
                    help="reuse cached answers but call the judge fresh (judge-consistency runs)")
    ap.add_argument("--budget", type=float, default=2000, help="hard cap in KRW for this run")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    splits = json.loads(SPLITS.read_text())
    items = [json.loads(l) | {"split": None} for l in GOLD.open() if l.strip()]
    for it in items:
        it["split"] = splits[it["id"]]
    if args.split != "all":
        items = [i for i in items if i["split"] == args.split]
    if args.ids:
        items = [i for i in items if i["id"] in args.ids.split(",")]

    opt = Options(strategy=args.strategy, top_k=args.k, inject_status=not args.no_inject,
                  expand_links=not args.no_links, tau=args.tau)
    cache = None if args.no_cache else CACHE
    gen = LLM(budget_krw=args.budget, cache_dir=cache)
    jdg = None if args.no_judge else LLM(budget_krw=args.budget,
                                         cache_dir=None if args.judge_no_cache else cache)
    out = ROOT / "runs" / f"{datetime.now():%Y%m%d-%H%M%S}_{args.name}"
    out.mkdir(parents=True)
    started = datetime.now().isoformat(timespec="seconds")
    print(f"{len(items)} items → {out.relative_to(ROOT)}  (budget {args.budget}원)")

    retriever(opt.strategy).search("워밍업", 1)  # load the embedder once, before worker threads
    results, aborted = {}, None
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {pool.submit(run_item, it, opt, gen, jdg): it for it in items}
        for f, it in futures.items():
            try:
                results[it["id"]] = f.result()
            except BudgetExceeded as e:
                aborted = str(e)
                pool.shutdown(cancel_futures=True)
                break
            spent = gen.spent_krw + (jdg.spent_krw if jdg else 0)
            print(f"  {it['id']:<6} {results[it['id']][0]['status']:<20} 누적 {spent:6.1f}원")
            if spent >= args.budget:
                aborted = f"budget {args.budget}원 reached"
                pool.shutdown(cancel_futures=True)
                break

    done = [it for it in items if it["id"] in results]
    preds = [results[i["id"]][0] for i in done]
    judgments = [results[i["id"]][1] for i in done if results[i["id"]][1]]
    jmap = {j["id"]: j for j in judgments}
    scores = [item_scores(it, results[it["id"]][0], jmap.get(it["id"])) for it in done]
    overall, levels, by_split = aggregate(scores), by_group(scores, "level"), by_group(scores, "split")

    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()  # noqa: E731
    usage = {k: getattr(gen.usage, k) + (getattr(jdg.usage, k) if jdg else 0) for k in asdict(gen.usage)}
    manifest = {
        "name": args.name, "started_at": started, "finished_at": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git("rev-parse", "--short", "HEAD"), "git_dirty": bool(git("status", "--porcelain", "--", "app", "eval")),
        "config": {k: v for k, v in vars(args).items() if k not in ("workers",)},
        "model": gen.model, "seed": SEED, "temperature": TEMPERATURE,
        "prompt_version": PROMPT_VERSION, "judge_version": J.JUDGE_VERSION,
        "embedding": json.loads((INDEX_DIR / args.strategy / "meta.json").read_text()),
        "gold_sha256": sha(GOLD), "splits_sha256": sha(SPLITS),
        "corpus_manifest_sha256": sha(ROOT / "data" / "manifest.json"),
        "usage": usage, "cost_krw": round(gen.spent_krw + (jdg.spent_krw if jdg else 0), 2),
        "items_planned": len(items), "items_done": len(done), "aborted": aborted,
    }
    manifest["embedding"] = f"{manifest['embedding']['embed_model']}@{manifest['embedding']['embed_revision'][:8]}"

    def dump(name, rows):
        (out / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    dump("predictions.jsonl", preds)
    dump("judgments.jsonl", judgments)
    dump("scores.jsonl", scores)
    (out / "report.json").write_text(json.dumps({"overall": overall, "by_level": levels, "by_split": by_split},
                                                ensure_ascii=False, indent=1))
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    (out / "report.md").write_text(report_md(args.name, overall, levels, by_split, scores, manifest))
    print(f"\n{len(done)}/{len(items)} items · {manifest['cost_krw']}원 · cache hits {usage['cache_hits']}"
          + (f" · ABORTED: {aborted}" if aborted else ""))
    for k in METRIC_KEYS:
        v = overall[k]
        print(f"  {k:<24} {'—' if v[0] is None else f'{v[0]:.3f}'}  (n={v[1]})")
    print(f"report: {(out / 'report.md').relative_to(ROOT)}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"elapsed {time.time() - t0:.0f}s")
