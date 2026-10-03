# 평가 리포트: v2-h1-fixed

- 실행: 2026-10-02T23:45:40 · git `b2c8efd` (dirty)
- 설정: {"name": "v2-h1-fixed", "strategy": "fixed", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": false, "reverse_refs": false, "prompt": "gen-v1", "precedents": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 400.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 175.79원 · LLM 호출 103회 · 캐시 적중 149회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.650 (n=100) |
| M1_recall_any | 0.935 (n=92) |
| M1_recall_all | 0.696 (n=92) |
| M1_mrr | 0.808 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.163 (n=92) |
| M3_citation_precision | 0.306 (n=77) |
| M3_citation_recall | 0.731 (n=92) |
| M4_kp_coverage | 0.735 (n=92) |
| M4_all_kp | 0.740 (n=77) |
| M4_complete | 0.620 (n=92) |
| M5_unsupported_rate | 0.058 (n=77) |
| M6_temporal_error | 0.154 (n=13) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 0.79 | 0.61 | 0.60 | 0.38 | 0.00 | 1.00 | 0.75 |
| M1_recall_any | 1.00 | 0.84 | 1.00 | 0.93 | 0.75 | 1.00 | — | 1.00 |
| M1_recall_all | 1.00 | 0.79 | 0.91 | 0.80 | 0.12 | 0.00 | — | 0.62 |
| M1_mrr | 0.93 | 0.75 | 0.91 | 0.75 | 0.60 | 0.76 | — | 0.85 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.16 | 0.09 | 0.13 | 0.25 | 0.67 | — | 0.00 |
| M3_citation_precision | 0.37 | 0.32 | 0.34 | 0.28 | 0.19 | 0.29 | — | 0.24 |
| M3_citation_recall | 1.00 | 0.84 | 0.78 | 0.80 | 0.42 | 0.14 | — | 0.82 |
| M4_kp_coverage | 1.00 | 0.82 | 0.80 | 0.73 | 0.58 | 0.07 | — | 0.93 |
| M4_all_kp | 1.00 | 0.94 | 0.67 | 0.69 | 0.50 | 0.00 | — | 0.75 |
| M4_complete | 1.00 | 0.79 | 0.61 | 0.60 | 0.38 | 0.00 | — | 0.75 |
| M5_unsupported_rate | 0.00 | 0.01 | 0.06 | 0.11 | 0.14 | 0.21 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.15 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.68 | 0.62 |
| M1_recall_any | 0.95 | 0.92 |
| M1_recall_all | 0.72 | 0.67 |
| M1_mrr | 0.88 | 0.75 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.12 | 0.19 |
| M3_citation_precision | 0.34 | 0.28 |
| M3_citation_recall | 0.78 | 0.69 |
| M4_kp_coverage | 0.76 | 0.71 |
| M4_all_kp | 0.74 | 0.74 |
| M4_complete | 0.65 | 0.60 |
| M5_unsupported_rate | 0.07 | 0.05 |
| M6_temporal_error | 0.17 | 0.14 |

## 확인이 필요한 문항 (46)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g013 | L2 | ans→ins(model_declined) | X | 0.00 | — | — |
| g014 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g017 | L2 | ans→ins(model_declined) | O | 0.00 | — | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.10 | — |
| g042 | L2 | ans→ins(model_declined) | X | 0.00 | — | — |
| g021 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g022 | L3 | ans→ins(model_declined) | O | 0.00 | — | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.25 | — |
| g024 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g027 | L3 | ans→ins(model_declined) | O | 0.00 | — | — |
| g028 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | 0.00 | — | — |
| g032 | L4 | ans→ans | O | 1.00 | 0.25 | O |
| g033 | L4 | ans→ans | O | 1.00 | 0.00 | X |
| g036 | L4 | ans→ans | O | 0.50 | 0.00 | X |
| g037 | L4 | ans→ans | O | 1.00 | 0.33 | O |
| l5a01 | L5a | ans→ans | O | 0.33 | 0.14 | — |
| l5a03 | L5a | ans→ans | O | 0.67 | 0.20 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | 0.00 | — | — |
| l5a05 | L5a | ans→ins(no_valid_citation) | X | 0.00 | — | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.00 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.40 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.09 | — |
| l5b01 | L5b | ans→ins(model_declined) | O | 0.00 | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | 0.00 | — | — |
| l5b03 | L5b | ans→ins(model_declined) | O | 0.00 | — | — |
| l5b04 | L5b | ans→ins(model_declined) | O | 0.00 | — | — |
| l5b05 | L5b | ans→ans | O | 0.33 | 0.00 | — |
| l5b06 | L5b | ans→ans | O | 0.33 | 0.50 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.67 | 0.00 | — |
| n01 | L3 | ans→ans | O | 1.00 | 0.14 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.12 | — |
| n06 | L3 | ans→ans | O | 0.33 | 0.33 | — |
| n13 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| n15 | L2 | ans→ans | O | 0.50 | 0.00 | — |
| n17 | L4 | ans→ins(retrieval_below_tau) | O | 0.00 | — | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.18 | O |
| n22 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| n23 | L4 | ans→ans | O | 0.50 | 0.17 | O |
| n24 | L4 | ans→ans | O | 0.50 | 0.50 | O |
| n25 | L3 | ans→ans | O | 0.67 | 0.45 | — |
| n29 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| l5b07 | L5b | ans→ins(model_declined) | O | 0.00 | — | — |
| l5b08 | L5b | ans→ins(model_declined) | O | 0.00 | — | — |
| l5b09 | L5b | ans→ans | O | 0.00 | 0.14 | — |
