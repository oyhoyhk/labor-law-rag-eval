# 평가 리포트: v2-h4-no-inject

- 실행: 2026-10-02T23:45:40 · git `b2c8efd` (dirty)
- 설정: {"name": "v2-h4-no-inject", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": true, "no_links": false, "siblings": false, "reverse_refs": false, "prompt": "gen-v1", "precedents": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 400.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 110.54원 · LLM 호출 97회 · 캐시 적중 158회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.924 (n=92) |
| M1_recall_all | 0.696 (n=92) |
| M1_mrr | 0.799 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.152 (n=92) |
| M3_citation_precision | 0.669 (n=78) |
| M3_citation_recall | 0.885 (n=78) |
| M4_kp_coverage | 0.818 (n=78) |
| M4_all_kp | 0.654 (n=78) |
| M4_complete | 0.554 (n=92) |
| M5_unsupported_rate | 0.020 (n=78) |
| M6_temporal_error | 0.273 (n=11) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 0.95 | 1.00 | 0.93 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.84 | 0.87 | 0.87 | 0.12 | 0.00 | — | 0.50 |
| M1_mrr | 0.95 | 0.73 | 0.95 | 0.77 | 0.75 | 0.46 | — | 0.84 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.05 | 0.04 | 0.27 | 0.12 | 0.78 | — | 0.00 |
| M3_citation_precision | 0.72 | 0.73 | 0.77 | 0.69 | 0.38 | 0.75 | — | 0.40 |
| M3_citation_recall | 1.00 | 1.00 | 0.91 | 1.00 | 0.53 | 0.38 | — | 0.70 |
| M4_kp_coverage | 1.00 | 0.98 | 0.88 | 0.46 | 0.73 | 0.33 | — | 0.76 |
| M4_all_kp | 1.00 | 0.94 | 0.73 | 0.09 | 0.43 | 0.00 | — | 0.50 |
| M4_complete | 1.00 | 0.90 | 0.70 | 0.07 | 0.38 | 0.00 | — | 0.50 |
| M5_unsupported_rate | 0.00 | 0.00 | 0.00 | 0.08 | 0.08 | 0.00 | — | 0.02 |
| M6_temporal_error | — | — | — | 0.27 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 0.95 | 0.90 |
| M1_recall_all | 0.68 | 0.71 |
| M1_mrr | 0.82 | 0.78 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.17 | 0.14 |
| M3_citation_precision | 0.65 | 0.69 |
| M3_citation_recall | 0.88 | 0.89 |
| M4_kp_coverage | 0.82 | 0.82 |
| M4_all_kp | 0.61 | 0.69 |
| M4_complete | 0.50 | 0.60 |
| M5_unsupported_rate | 0.00 | 0.03 |
| M6_temporal_error | 0.40 | 0.17 |

## 확인이 필요한 문항 (46)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g013 | L2 | ans→ins(model_declined) | O | — | — | — |
| g020 | L2 | ans→ans | O | 0.67 | 0.00 | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| g022 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| g025 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| g028 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | — | — | — |
| g032 | L4 | ans→ans | O | 0.33 | 0.33 | O |
| g033 | L4 | ans→ans | O | 1.00 | 0.00 | X |
| g034 | L4 | ans→ans | O | 0.67 | 0.00 | X |
| g035 | L4 | ans→ans | O | 0.33 | 0.00 | O |
| g036 | L4 | ans→ans | O | 0.50 | 0.00 | X |
| g037 | L4 | ans→ans | O | 0.33 | 0.00 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.22 | — |
| l5a02 | L5a | ans→ans | O | 0.75 | 0.00 | — |
| l5a03 | L5a | ans→ans | O | 0.67 | 0.00 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | — | — | — |
| l5a05 | L5a | ans→ans | X | 0.00 | 0.00 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.00 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.14 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.17 | — |
| l5b01 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | — | — | — |
| l5b03 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b04 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b05 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b06 | L5b | ans→ans | O | 0.67 | 0.00 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.14 | — |
| n01 | L3 | ans→ins(model_declined) | O | — | — | — |
| n08 | L3 | ans→ans | O | 0.67 | 0.09 | — |
| n17 | L4 | ans→ans | O | 0.33 | 0.00 | O |
| n18 | L4 | ans→ans | O | 0.50 | 0.33 | O |
| n19 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| n20 | L4 | ans→ans | O | 0.50 | 0.17 | O |
| n21 | L4 | ans→ins(model_declined) | O | — | — | — |
| n22 | L4 | ans→ins(model_declined) | O | — | — | — |
| n23 | L4 | ans→ans | O | 0.00 | 0.00 | O |
| n24 | L4 | ans→ins(model_declined) | O | — | — | — |
| n25 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| l5b07 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b08 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b09 | L5b | ans→ans | O | 0.00 | 0.00 | — |
| s07 | SUM | ans→ans | O | 0.75 | 0.00 | — |
| s08 | SUM | ans→ans | O | 0.20 | 0.00 | — |
