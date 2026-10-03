# 평가 리포트: v2-precedents

- 실행: 2026-10-02T23:51:43 · git `b2c8efd` (dirty)
- 설정: {"name": "v2-precedents", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": false, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 200.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 58.65원 · LLM 호출 33회 · 캐시 적중 241회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.780 (n=100) |
| M1_recall_any | 0.924 (n=92) |
| M1_recall_all | 0.696 (n=92) |
| M1_mrr | 0.799 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.065 (n=92) |
| M3_citation_precision | 0.609 (n=86) |
| M3_citation_recall | 0.820 (n=92) |
| M4_kp_coverage | 0.841 (n=92) |
| M4_all_kp | 0.814 (n=86) |
| M4_complete | 0.761 (n=92) |
| M5_unsupported_rate | 0.053 (n=86) |
| M6_temporal_error | 0.000 (n=14) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 0.90 | 0.78 | 0.73 | 0.75 | 0.44 | 1.00 | 0.50 |
| M1_recall_any | 1.00 | 0.95 | 1.00 | 0.93 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.84 | 0.87 | 0.87 | 0.12 | 0.00 | — | 0.50 |
| M1_mrr | 0.95 | 0.73 | 0.95 | 0.77 | 0.75 | 0.46 | — | 0.84 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.07 | 0.12 | 0.44 | — | 0.00 |
| M3_citation_precision | 0.72 | 0.69 | 0.65 | 0.56 | 0.35 | 0.80 | — | 0.37 |
| M3_citation_recall | 1.00 | 0.97 | 0.88 | 0.87 | 0.47 | 0.50 | — | 0.70 |
| M4_kp_coverage | 1.00 | 0.91 | 0.90 | 0.81 | 0.83 | 0.52 | — | 0.73 |
| M4_all_kp | 1.00 | 0.90 | 0.78 | 0.79 | 0.86 | 0.80 | — | 0.50 |
| M4_complete | 1.00 | 0.90 | 0.78 | 0.73 | 0.75 | 0.44 | — | 0.50 |
| M5_unsupported_rate | 0.00 | 0.04 | 0.07 | 0.04 | 0.09 | 0.12 | — | 0.03 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.70 | 0.84 |
| M1_recall_any | 0.95 | 0.90 |
| M1_recall_all | 0.68 | 0.71 |
| M1_mrr | 0.82 | 0.78 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.05 | 0.08 |
| M3_citation_precision | 0.57 | 0.64 |
| M3_citation_recall | 0.81 | 0.83 |
| M4_kp_coverage | 0.81 | 0.86 |
| M4_all_kp | 0.71 | 0.90 |
| M4_complete | 0.68 | 0.83 |
| M5_unsupported_rate | 0.05 | 0.05 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (44)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g011 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| g012 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g013 | L2 | ans→ans | O | 0.00 | 0.25 | — |
| g016 | L2 | ans→ans | O | 1.00 | 0.11 | — |
| g018 | L2 | ans→ans | O | 0.33 | 0.00 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.11 | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.33 | 0.08 | — |
| g022 | L3 | ans→ans | O | 1.00 | 0.33 | — |
| g023 | L3 | ans→ans | O | 0.50 | 0.60 | — |
| g025 | L3 | ans→ans | O | 1.00 | 0.33 | — |
| g031 | L4 | ans→ins(model_declined) | X | 0.00 | — | — |
| g032 | L4 | ans→ans | O | 1.00 | 0.17 | O |
| g034 | L4 | ans→ans | O | 1.00 | 0.08 | O |
| g035 | L4 | ans→ans | O | 0.67 | 0.00 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | 0.00 | — | — |
| l5a05 | L5a | ans→ans | X | 1.00 | 0.20 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.08 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5b01 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | 0.00 | — | — |
| l5b03 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b05 | L5b | ans→ans | O | 1.00 | 0.09 | — |
| l5b06 | L5b | ans→ans | O | 1.00 | 0.12 | — |
| s01 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.07 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.05 | — |
| n01 | L3 | ans→ans | O | 0.50 | 0.09 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n05 | L3 | ans→ans | O | 1.00 | 0.14 | — |
| n12 | L2 | ans→ans | O | 1.00 | 0.11 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n19 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| n22 | L4 | ans→ans | O | 1.00 | 0.07 | O |
| n23 | L4 | ans→ans | O | 0.00 | 0.14 | O |
| n25 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.40 | — |
| l5b08 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b09 | L5b | ans→ans | O | 0.67 | 0.00 | — |
| s06 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s07 | SUM | ans→ans | O | 0.50 | 0.00 | — |
| s08 | SUM | ans→ans | O | 0.20 | 0.07 | — |
