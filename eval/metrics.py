"""Per-item scores and aggregation. Deterministic metrics need no LLM; judge metrics read judgments."""

from collections import defaultdict
from statistics import mean

ANSWERABLE = {"L1", "L2", "L3", "L4", "L5a"}


def item_scores(item: dict, pred: dict, judgment: dict | None) -> dict:
    gold = set(item["gold_evidence"])
    searched = [r for r in pred["retrieval"] if not r["linked"]]
    ranks = [r["rank"] for r in searched if gold & set(r["article_ids"])]
    found_search = {a for r in searched for a in r["article_ids"]} & gold
    found_any = {a for r in pred["retrieval"] for a in r["article_ids"]} & gold
    cited = {a for c in pred["citations"] for a in c["article_ids"]}
    expected_answer = item["expected_status"] == "answered"
    answered = pred["status"] == "answered"

    s = {
        "id": item["id"], "level": item["level"], "split": item.get("split"),
        "expected": item["expected_status"], "status": pred["status"],
        "refusal_reason": pred["meta"].get("refusal_reason"),
        # M1 retrieval (search hits only; link expansion reported separately)
        "m1_recall_any": bool(ranks) if gold else None,
        "m1_recall_all": (found_search == gold) if gold else None,
        "m1_rr": (1 / min(ranks) if ranks else 0.0) if gold else None,
        "m1_with_links_any": bool(found_any) if gold else None,
        # M2 refusal. A refusal-expected item (OOS, and L5b in gold v1/v1.1) passes when the system refuses
        # (no article above τ, or the model declines) or answers while stating the corpus has no basis for the
        # conclusion (Judge asserts_conclusion false, e.g. a premise correction). From v2.1 L5b expects a
        # precedent-citing answer and is scored like any answerable item.
        "m2_correct_status": (not answered or (judgment or {}).get("grade", {}).get("asserts_conclusion") is False)
        if not expected_answer else answered == expected_answer,
        # M3 citations. Precision over answered items only (a refusal cites nothing); recall over every answerable
        # item, a refusal counting 0, so refusing hard items cannot raise it.
        "m3_citation_precision": (len(cited & gold) / len(cited) if cited else None) if answered and gold else None,
        "m3_citation_recall": ((len(cited & gold) / len(gold)) if answered else 0.0) if expected_answer and gold else None,
        "cost_krw": pred["meta"].get("cost_krw", 0.0), "latency_ms": pred["meta"].get("latency_ms"),
    }
    # How a refusal-expected item was handled: gate (nothing above τ) | declined (model refused) | hedged
    # (answered without asserting a conclusion) | asserted (a miss).
    if not expected_answer:
        hedged = (judgment or {}).get("grade", {}).get("asserts_conclusion") is False
        s["refusal_mode"] = ("gate" if pred["meta"].get("refusal_reason") == "retrieval_below_tau" else "declined"
                             ) if not answered else ("hedged" if hedged else "asserted")
    # End to end: an answerable item answered with every key point. A refusal counts as a miss.
    s["m4_complete"] = None if not expected_answer else False
    # Key-point coverage counts a refused answerable item as 0 for the same reason as citation recall.
    if expected_answer and not answered and item["key_points"]:
        s["m4_kp_coverage"] = 0.0
    if judgment and answered:
        g, gr = judgment.get("grade", {}), judgment.get("grounding", {})
        kps = g.get("key_points", [])
        # A key point later removed from the gold set (CHANGELOG) no longer counts; matched by its text.
        if any(k.get("key_point") in item["key_points"] for k in kps):
            kps = [k for k in kps if k.get("key_point") in item["key_points"]]
        if kps and expected_answer:
            s["m4_kp_coverage"] = mean(k["asserted"] for k in kps)
            s["m4_all_kp"] = all(k["asserted"] for k in kps)
            s["m4_complete"] = s["m4_all_kp"]
        if gr.get("n_claims"):
            s["m5_unsupported_rate"] = gr["n_unsupported"] / gr["n_claims"]
        if "temporal_error" in g:
            s["m6_temporal_error"] = bool(g["temporal_error"])
        if "asserts_conclusion" in g:
            s["soft_refusal_ok"] = not g["asserts_conclusion"]
    # M0 overall accuracy over all items: answerable → complete answer, refusal-expected → correct refusal.
    s["m0_correct"] = bool(s["m4_complete"]) if expected_answer else s["m2_correct_status"]
    return s


def _avg(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return (round(mean(float(v) for v in vals), 3), len(vals)) if vals else (None, 0)


def aggregate(rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["expected"] == "answered"]
    refusable = [r for r in rows if r["expected"] != "answered"]
    out = {
        "n": len(rows),
        "M0_accuracy": _avg(rows, "m0_correct"),
        "M1_recall_any": _avg(rows, "m1_recall_any"), "M1_recall_all": _avg(rows, "m1_recall_all"),
        "M1_mrr": _avg(rows, "m1_rr"), "M1_with_links_any": _avg(rows, "m1_with_links_any"),
        # M2: out-of-corpus refusal, L5b no-assertion (refuse or hedge; refusal-expected L5b only, None when
        # absent), over-refusal of answerable items (includes v2.1 precedent-citing L5b)
        "M2_oos_refusal": _avg([r for r in refusable if r["level"] == "OOS"], "m2_correct_status"),
        "M2_l5b_no_assertion": _avg([{"v": r["status"] != "answered" or r.get("soft_refusal_ok") is True}
                                     for r in refusable if r["level"] == "L5b"], "v"),
        "M2_over_refusal": _avg([{"v": r["status"] != "answered"} for r in answerable], "v"),
        "M3_citation_precision": _avg(rows, "m3_citation_precision"),
        "M3_citation_recall": _avg(rows, "m3_citation_recall"),
        "M4_kp_coverage": _avg(rows, "m4_kp_coverage"), "M4_all_kp": _avg(rows, "m4_all_kp"),
        "M4_complete": _avg(rows, "m4_complete"),
        "M5_unsupported_rate": _avg(rows, "m5_unsupported_rate"),
        "M6_temporal_error": _avg(rows, "m6_temporal_error"),
        "cost_krw": round(sum(r["cost_krw"] or 0 for r in rows), 2),
        "latency_ms_p50": sorted(r["latency_ms"] or 0 for r in rows)[len(rows) // 2] if rows else None,
    }
    return out


def by_group(rows: list[dict], key: str) -> dict:
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    return {g: aggregate(rs) for g, rs in sorted(groups.items(), key=lambda x: str(x[0]))}
