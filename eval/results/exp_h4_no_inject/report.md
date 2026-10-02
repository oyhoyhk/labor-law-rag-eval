# 평가 리포트: exp-h4-no-inject

- 실행: 2026-10-02T11:04:43 · git `d84a500`
- 설정: {"name": "exp-h4-no-inject", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": true, "no_links": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 300.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 185.06원 · LLM 호출 157회 · 캐시 적중 2회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.895 (n=57) |
| M1_recall_all | 0.702 (n=57) |
| M1_mrr | 0.786 (n=57) |
| M2_oos_refusal | 1.000 (n=4) |
| M2_l5b_no_assertion | 1.000 (n=6) |
| M2_over_refusal | 0.059 (n=51) |
| M3_citation_precision | 0.679 (n=49) |
| M3_citation_recall | 0.889 (n=49) |
| M4_kp_coverage | 0.834 (n=48) |
| M4_all_kp | 0.667 (n=48) |
| M5_unsupported_rate | 0.021 (n=49) |
| M6_temporal_error | 0.500 (n=6) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 0.91 | 1.00 | 0.86 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.73 | 0.90 | 0.86 | 0.12 | 0.50 | — | 0.60 |
| M1_mrr | 0.95 | 0.73 | 0.93 | 0.79 | 0.75 | 0.47 | — | 0.74 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | 1.00 | — | — |
| M2_over_refusal | 0.00 | 0.09 | 0.00 | 0.14 | 0.12 | — | — | 0.00 |
| M3_citation_precision | 0.72 | 0.71 | 0.87 | 0.92 | 0.38 | 0.50 | — | 0.31 |
| M3_citation_recall | 1.00 | 1.00 | 0.90 | 1.00 | 0.53 | 1.00 | — | 0.77 |
| M4_kp_coverage | 1.00 | 0.97 | 0.80 | 0.53 | 0.73 | — | — | 0.83 |
| M4_all_kp | 1.00 | 0.90 | 0.60 | 0.17 | 0.43 | — | — | 0.60 |
| M5_unsupported_rate | 0.00 | 0.00 | 0.00 | 0.06 | 0.08 | 0.00 | — | 0.03 |
| M6_temporal_error | — | — | — | 0.50 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 0.91 | 0.89 |
| M1_recall_all | 0.73 | 0.69 |
| M1_mrr | 0.80 | 0.78 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | 1.00 | 1.00 |
| M2_over_refusal | 0.10 | 0.03 |
| M3_citation_precision | 0.67 | 0.69 |
| M3_citation_recall | 0.92 | 0.87 |
| M4_kp_coverage | 0.88 | 0.81 |
| M4_all_kp | 0.67 | 0.67 |
| M5_unsupported_rate | 0.00 | 0.03 |
| M6_temporal_error | 0.67 | 0.33 |

## 확인이 필요한 문항 (26)

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
| l5b01 | L5b | ins→ins(model_declined) | X | — | — | — |
| l5b03 | L5b | ins→ins(model_declined) | X | — | — | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.14 | — |
