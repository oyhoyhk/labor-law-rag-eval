# 평가 리포트: v2-k10

- 실행: 2026-10-02T23:45:40 · git `b2c8efd` (dirty)
- 설정: {"name": "v2-k10", "strategy": "article", "k": 10, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": false, "reverse_refs": false, "prompt": "gen-v1", "precedents": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 400.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 170.88원 · LLM 호출 103회 · 캐시 적중 157회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.967 (n=92) |
| M1_recall_all | 0.815 (n=92) |
| M1_mrr | 0.805 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.120 (n=92) |
| M3_citation_precision | 0.674 (n=81) |
| M3_citation_recall | 0.903 (n=81) |
| M4_kp_coverage | 0.932 (n=81) |
| M4_all_kp | 0.864 (n=81) |
| M4_complete | 0.761 (n=92) |
| M5_unsupported_rate | 0.027 (n=81) |
| M6_temporal_error | 0.000 (n=13) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 1.00 | 1.00 | 0.93 | 0.88 | 0.89 | — | 1.00 |
| M1_recall_all | 1.00 | 0.95 | 1.00 | 0.87 | 0.50 | 0.00 | — | 0.88 |
| M1_mrr | 0.95 | 0.74 | 0.95 | 0.77 | 0.76 | 0.50 | — | 0.84 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.05 | 0.04 | 0.13 | 0.12 | 0.67 | — | 0.00 |
| M3_citation_precision | 0.72 | 0.66 | 0.81 | 0.67 | 0.56 | 0.58 | — | 0.42 |
| M3_citation_recall | 1.00 | 1.00 | 0.89 | 0.89 | 0.70 | 0.50 | — | 0.97 |
| M4_kp_coverage | 1.00 | 0.98 | 0.93 | 0.89 | 1.00 | 0.33 | — | 0.97 |
| M4_all_kp | 1.00 | 0.94 | 0.82 | 0.85 | 1.00 | 0.00 | — | 0.88 |
| M4_complete | 1.00 | 0.90 | 0.78 | 0.73 | 0.88 | 0.00 | — | 0.88 |
| M5_unsupported_rate | 0.00 | 0.01 | 0.01 | 0.07 | 0.12 | 0.03 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 1.00 | 0.94 |
| M1_recall_all | 0.80 | 0.83 |
| M1_mrr | 0.83 | 0.79 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.15 | 0.10 |
| M3_citation_precision | 0.65 | 0.69 |
| M3_citation_recall | 0.90 | 0.90 |
| M4_kp_coverage | 0.92 | 0.94 |
| M4_all_kp | 0.82 | 0.89 |
| M4_complete | 0.70 | 0.81 |
| M5_unsupported_rate | 0.01 | 0.04 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (31)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g013 | L2 | ans→ins(model_declined) | O | — | — | — |
| g018 | L2 | ans→ans | O | 1.00 | 0.11 | — |
| g020 | L2 | ans→ans | O | 0.67 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g024 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g029 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | — | — | — |
| g032 | L4 | ans→ans | O | 1.00 | 0.33 | O |
| g033 | L4 | ans→ins(model_declined) | O | — | — | — |
| g037 | L4 | ans→ans | O | 1.00 | 0.50 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.25 | — |
| l5a02 | L5a | ans→ans | O | 1.00 | 0.25 | — |
| l5a04 | L5a | ans→ins(model_declined) | O | — | — | — |
| l5a05 | L5a | ans→ans | X | 1.00 | 0.20 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.14 | — |
| l5b01 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | — | — | — |
| l5b03 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b04 | L5b | ans→ins(no_valid_citation) | O | — | — | — |
| l5b05 | L5b | ans→ans | O | 0.33 | 0.08 | — |
| l5b06 | L5b | ans→ans | O | 0.33 | 0.00 | — |
| n01 | L3 | ans→ins(model_declined) | O | — | — | — |
| n04 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| n08 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n23 | L4 | ans→ans | O | 0.00 | 0.00 | O |
| n24 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| l5b07 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b08 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b09 | L5b | ans→ans | O | 0.33 | 0.00 | — |
| s08 | SUM | ans→ans | O | 0.80 | 0.00 | — |
