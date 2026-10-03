# 평가 리포트: noise-v2-3

- 실행: 2026-10-02T23:41:03 · git `b2c8efd` (dirty)
- 설정: {"name": "noise-v2-3", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": false, "reverse_refs": false, "prompt": "gen-v1", "precedents": false, "split": "all", "ids": "", "no_judge": false, "no_cache": true, "judge_no_cache": false, "budget": 400.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 217.08원 · LLM 호출 264회 · 캐시 적중 0회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.720 (n=100) |
| M1_recall_any | 0.924 (n=92) |
| M1_recall_all | 0.696 (n=92) |
| M1_mrr | 0.799 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.098 (n=92) |
| M3_citation_precision | 0.699 (n=83) |
| M3_citation_recall | 0.753 (n=92) |
| M4_kp_coverage | 0.786 (n=92) |
| M4_all_kp | 0.771 (n=83) |
| M4_complete | 0.696 (n=92) |
| M5_unsupported_rate | 0.023 (n=83) |
| M6_temporal_error | 0.000 (n=14) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 0.84 | 0.83 | 0.73 | 0.50 | 0.00 | 1.00 | 0.50 |
| M1_recall_any | 1.00 | 0.95 | 1.00 | 0.93 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.84 | 0.87 | 0.87 | 0.12 | 0.00 | — | 0.50 |
| M1_mrr | 0.95 | 0.73 | 0.95 | 0.77 | 0.75 | 0.46 | — | 0.84 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.05 | 0.00 | 0.07 | 0.12 | 0.67 | — | 0.00 |
| M3_citation_precision | 0.71 | 0.74 | 0.80 | 0.74 | 0.48 | 0.67 | — | 0.43 |
| M3_citation_recall | 1.00 | 0.95 | 0.81 | 0.80 | 0.47 | 0.14 | — | 0.70 |
| M4_kp_coverage | 1.00 | 0.90 | 0.91 | 0.83 | 0.67 | 0.07 | — | 0.73 |
| M4_all_kp | 1.00 | 0.89 | 0.83 | 0.79 | 0.57 | 0.00 | — | 0.50 |
| M4_complete | 1.00 | 0.84 | 0.83 | 0.73 | 0.50 | 0.00 | — | 0.50 |
| M5_unsupported_rate | 0.00 | 0.01 | 0.00 | 0.05 | 0.07 | 0.11 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.73 | 0.71 |
| M1_recall_any | 0.95 | 0.90 |
| M1_recall_all | 0.68 | 0.71 |
| M1_mrr | 0.82 | 0.78 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.10 | 0.10 |
| M3_citation_precision | 0.70 | 0.70 |
| M3_citation_recall | 0.74 | 0.76 |
| M4_kp_coverage | 0.78 | 0.79 |
| M4_all_kp | 0.78 | 0.77 |
| M4_complete | 0.70 | 0.69 |
| M5_unsupported_rate | 0.02 | 0.02 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (34)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g012 | L2 | ans→ans | O | 0.50 | 0.00 | — |
| g013 | L2 | ans→ins(model_declined) | O | 0.00 | — | — |
| g020 | L2 | ans→ans | O | 0.67 | 0.20 | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| g024 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | 0.00 | — | — |
| g032 | L4 | ans→ans | O | 1.00 | 0.33 | O |
| g033 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| g036 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a03 | L5a | ans→ans | O | 0.67 | 0.00 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | 0.00 | — | — |
| l5a05 | L5a | ans→ans | X | 0.00 | 0.20 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.18 | — |
| l5b01 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | 0.00 | — | — |
| l5b03 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b04 | L5b | ans→ins(model_declined) | O | 0.00 | — | — |
| l5b05 | L5b | ans→ans | O | 0.33 | 0.00 | — |
| l5b06 | L5b | ans→ans | O | 0.33 | 0.33 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.00 | — |
| n01 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| n08 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.13 | O |
| n19 | L4 | ans→ans | O | 1.00 | 0.14 | O |
| n23 | L4 | ans→ans | O | 0.50 | 0.14 | O |
| n25 | L3 | ans→ans | O | 1.00 | 0.09 | — |
| l5b07 | L5b | ans→ins(model_declined) | O | 0.00 | — | — |
| l5b08 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b09 | L5b | ans→ans | O | 0.00 | 0.00 | — |
| s07 | SUM | ans→ans | O | 0.50 | 0.00 | — |
| s08 | SUM | ans→ans | O | 0.20 | 0.00 | — |
