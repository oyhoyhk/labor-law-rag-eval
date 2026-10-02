# 평가 리포트: v2-hybrid

- 실행: 2026-10-03T02:18:04 · git `1be2178` (dirty)
- 설정: {"name": "v2-hybrid", "strategy": "whole", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "hybrid": true, "fewshot_dev": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 600.0, "hybrid_params": {"n": 50, "rrf_k": 60, "bm25_weight": 0.5, "k1": 1.5, "b": 0.75}}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 503.94원 · LLM 호출 255회 · 캐시 적중 22회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.946 (n=92) |
| M1_recall_all | 0.707 (n=92) |
| M1_mrr | 0.804 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.043 (n=92) |
| M3_citation_precision | 0.527 (n=88) |
| M3_citation_recall | 0.864 (n=88) |
| M4_kp_coverage | 0.886 (n=88) |
| M4_all_kp | 0.795 (n=88) |
| M4_complete | 0.761 (n=92) |
| M5_unsupported_rate | 0.056 (n=88) |
| M6_temporal_error | 0.000 (n=15) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 1.00 | 1.00 | 0.93 | 0.75 | 0.78 | — | 1.00 |
| M1_recall_all | 1.00 | 0.95 | 0.87 | 0.80 | 0.12 | 0.00 | — | 0.50 |
| M1_mrr | 0.90 | 0.79 | 0.94 | 0.72 | 0.69 | 0.52 | — | 0.94 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.00 | 0.12 | 0.33 | — | 0.00 |
| M3_citation_precision | 0.71 | 0.49 | 0.56 | 0.48 | 0.31 | 0.71 | — | 0.41 |
| M3_citation_recall | 1.00 | 0.97 | 0.85 | 0.87 | 0.51 | 0.85 | — | 0.77 |
| M4_kp_coverage | 0.95 | 0.90 | 0.88 | 0.87 | 0.81 | 0.94 | — | 0.85 |
| M4_all_kp | 0.90 | 0.84 | 0.78 | 0.87 | 0.71 | 0.83 | — | 0.50 |
| M4_complete | 0.90 | 0.84 | 0.78 | 0.87 | 0.62 | 0.56 | — | 0.50 |
| M5_unsupported_rate | 0.00 | 0.06 | 0.06 | 0.05 | 0.16 | 0.07 | — | 0.04 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 0.95 | 0.94 |
| M1_recall_all | 0.65 | 0.75 |
| M1_mrr | 0.81 | 0.80 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.05 | 0.04 |
| M3_citation_precision | 0.51 | 0.54 |
| M3_citation_recall | 0.87 | 0.86 |
| M4_kp_coverage | 0.89 | 0.88 |
| M4_all_kp | 0.82 | 0.78 |
| M4_complete | 0.78 | 0.75 |
| M5_unsupported_rate | 0.06 | 0.06 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (47)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g003 | L1 | ans→ans | O | 0.50 | 0.00 | — |
| g011 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g012 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g013 | L2 | ans→ans | O | 0.00 | 0.22 | — |
| g018 | L2 | ans→ans | O | 0.33 | 0.00 | — |
| g020 | L2 | ans→ans | O | 0.67 | 0.11 | — |
| g021 | L3 | ans→ans | O | 0.67 | 0.06 | — |
| g022 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.50 | — |
| g024 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g025 | L3 | ans→ans | O | 1.00 | 0.12 | — |
| g028 | L3 | ans→ans | O | 0.00 | 0.00 | — |
| g031 | L4 | ans→ans | X | 0.00 | 0.00 | O |
| g033 | L4 | ans→ans | O | 1.00 | 0.14 | O |
| g034 | L4 | ans→ans | O | 1.00 | 0.05 | O |
| g037 | L4 | ans→ans | O | 1.00 | 0.14 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.10 | — |
| l5a02 | L5a | ans→ans | O | 1.00 | 0.08 | — |
| l5a03 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | — | — | — |
| l5a05 | L5a | ans→ans | X | 0.00 | 0.40 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.14 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.17 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.08 | — |
| l5b01 | L5b | ans→ans | O | 0.67 | 0.17 | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | — | — | — |
| l5b03 | L5b | ans→ins(model_declined) | X | — | — | — |
| s01 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.03 | — |
| s05 | SUM | ans→ans | O | 0.67 | 0.07 | — |
| n01 | L3 | ans→ans | O | 0.50 | 0.12 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n04 | L3 | ans→ans | O | 1.00 | 0.11 | — |
| n06 | L3 | ans→ans | O | 1.00 | 0.10 | — |
| n08 | L3 | ans→ans | O | 1.00 | 0.09 | — |
| n11 | L2 | ans→ans | O | 1.00 | 0.10 | — |
| n12 | L2 | ans→ans | O | 1.00 | 0.20 | — |
| n15 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n22 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n23 | L4 | ans→ans | O | 0.00 | 0.17 | O |
| n25 | L3 | ans→ans | O | 1.00 | 0.06 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.10 | — |
| l5b08 | L5b | ans→ins(no_valid_citation) | X | — | — | — |
| l5b09 | L5b | ans→ans | O | 1.00 | 0.12 | — |
| s07 | SUM | ans→ans | O | 0.75 | 0.08 | — |
| s08 | SUM | ans→ans | O | 0.60 | 0.10 | — |
