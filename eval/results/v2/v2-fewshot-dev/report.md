# 평가 리포트: v2-fewshot-dev

- 실행: 2026-10-03T02:18:00 · git `1be2178` (dirty)
- 설정: {"name": "v2-fewshot-dev", "strategy": "whole", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent+fewshot-dev", "precedents": true, "hybrid": false, "fewshot_dev": true, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 600.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 520.56원 · LLM 호출 271회 · 캐시 적중 0회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.830 (n=100) |
| M1_recall_any | 0.924 (n=92) |
| M1_recall_all | 0.696 (n=92) |
| M1_mrr | 0.801 (n=92) |
| M2_oos_refusal | 0.875 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.076 (n=92) |
| M3_citation_precision | 0.660 (n=85) |
| M3_citation_recall | 0.824 (n=92) |
| M4_kp_coverage | 0.876 (n=92) |
| M4_all_kp | 0.894 (n=85) |
| M4_complete | 0.826 (n=92) |
| M5_unsupported_rate | 0.040 (n=86) |
| M6_temporal_error | 0.000 (n=14) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 0.95 | 0.91 | 0.87 | 0.75 | 0.44 | 0.88 | 0.50 |
| M1_recall_any | 1.00 | 0.95 | 1.00 | 0.93 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.84 | 0.87 | 0.87 | 0.12 | 0.00 | — | 0.50 |
| M1_mrr | 0.95 | 0.78 | 0.92 | 0.77 | 0.75 | 0.44 | — | 0.84 |
| M2_oos_refusal | — | — | — | — | — | — | 0.88 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.05 | 0.00 | 0.07 | 0.12 | 0.44 | — | 0.00 |
| M3_citation_precision | 0.73 | 0.66 | 0.77 | 0.63 | 0.36 | 1.00 | — | 0.34 |
| M3_citation_recall | 1.00 | 0.95 | 0.89 | 0.90 | 0.47 | 0.50 | — | 0.70 |
| M4_kp_coverage | 1.00 | 0.95 | 0.96 | 0.87 | 0.83 | 0.52 | — | 0.76 |
| M4_all_kp | 1.00 | 1.00 | 0.91 | 0.93 | 0.86 | 0.80 | — | 0.50 |
| M4_complete | 1.00 | 0.95 | 0.91 | 0.87 | 0.75 | 0.44 | — | 0.50 |
| M5_unsupported_rate | 0.00 | 0.02 | 0.03 | 0.05 | 0.15 | 0.06 | 0.00 | 0.06 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.80 | 0.86 |
| M1_recall_any | 0.95 | 0.90 |
| M1_recall_all | 0.68 | 0.71 |
| M1_mrr | 0.82 | 0.79 |
| M2_oos_refusal | 0.75 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.07 | 0.08 |
| M3_citation_precision | 0.65 | 0.67 |
| M3_citation_recall | 0.82 | 0.83 |
| M4_kp_coverage | 0.87 | 0.88 |
| M4_all_kp | 0.86 | 0.92 |
| M4_complete | 0.80 | 0.85 |
| M5_unsupported_rate | 0.03 | 0.05 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (40)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g011 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g012 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g013 | L2 | ans→ins(no_valid_citation) | O | 0.00 | — | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 1.00 | 0.07 | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g025 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g031 | L4 | ans→ins(model_declined) | X | 0.00 | — | — |
| g032 | L4 | ans→ans | O | 1.00 | 0.20 | O |
| g034 | L4 | ans→ans | O | 1.00 | 0.07 | O |
| g037 | L4 | ans→ans | O | 1.00 | 0.29 | O |
| g041 | OOS | ins→ans | — | — | 0.00 | — |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.10 | — |
| l5a03 | L5a | ans→ans | O | 1.00 | 0.17 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | 0.00 | — | — |
| l5a05 | L5a | ans→ans | X | 1.00 | 0.42 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.20 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.07 | — |
| l5b01 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | 0.00 | — | — |
| l5b03 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b05 | L5b | ans→ans | O | 1.00 | 0.10 | — |
| l5b06 | L5b | ans→ans | O | 1.00 | 0.10 | — |
| s01 | SUM | ans→ans | O | 1.00 | 0.05 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.08 | — |
| n01 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n05 | L3 | ans→ans | O | 1.00 | 0.11 | — |
| n12 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.08 | O |
| n23 | L4 | ans→ans | O | 0.00 | 0.00 | O |
| n25 | L3 | ans→ans | O | 1.00 | 0.10 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.10 | — |
| l5b08 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b09 | L5b | ans→ans | O | 0.67 | 0.00 | — |
| s06 | SUM | ans→ans | O | 1.00 | 0.04 | — |
| s07 | SUM | ans→ans | O | 0.75 | 0.08 | — |
| s08 | SUM | ans→ans | O | 0.20 | 0.19 | — |
