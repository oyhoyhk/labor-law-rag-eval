# 평가 리포트: noise-v2-2

- 실행: 2026-10-02T23:41:01 · git `b2c8efd` (dirty)
- 설정: {"name": "noise-v2-2", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": false, "reverse_refs": false, "prompt": "gen-v1", "precedents": false, "split": "all", "ids": "", "no_judge": false, "no_cache": true, "judge_no_cache": false, "budget": 400.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 282.53원 · LLM 호출 260회 · 캐시 적중 0회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.924 (n=92) |
| M1_recall_all | 0.696 (n=92) |
| M1_mrr | 0.799 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.120 (n=92) |
| M3_citation_precision | 0.692 (n=81) |
| M3_citation_recall | 0.870 (n=81) |
| M4_kp_coverage | 0.865 (n=81) |
| M4_all_kp | 0.741 (n=81) |
| M4_complete | 0.652 (n=92) |
| M5_unsupported_rate | 0.009 (n=81) |
| M6_temporal_error | 0.000 (n=13) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 0.95 | 1.00 | 0.93 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.84 | 0.87 | 0.87 | 0.12 | 0.00 | — | 0.50 |
| M1_mrr | 0.95 | 0.73 | 0.95 | 0.77 | 0.75 | 0.46 | — | 0.84 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.13 | 0.12 | 0.78 | — | 0.12 |
| M3_citation_precision | 0.71 | 0.75 | 0.75 | 0.74 | 0.51 | 0.75 | — | 0.41 |
| M3_citation_recall | 1.00 | 0.97 | 0.90 | 0.89 | 0.53 | 0.38 | — | 0.76 |
| M4_kp_coverage | 1.00 | 0.90 | 0.88 | 0.86 | 0.77 | 0.17 | — | 0.81 |
| M4_all_kp | 1.00 | 0.84 | 0.74 | 0.77 | 0.43 | 0.00 | — | 0.57 |
| M4_complete | 1.00 | 0.84 | 0.74 | 0.67 | 0.38 | 0.00 | — | 0.50 |
| M5_unsupported_rate | 0.00 | 0.01 | 0.01 | 0.02 | 0.01 | 0.00 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 0.95 | 0.90 |
| M1_recall_all | 0.68 | 0.71 |
| M1_mrr | 0.82 | 0.78 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.12 | 0.12 |
| M3_citation_precision | 0.66 | 0.72 |
| M3_citation_recall | 0.88 | 0.86 |
| M4_kp_coverage | 0.84 | 0.88 |
| M4_all_kp | 0.69 | 0.78 |
| M4_complete | 0.60 | 0.69 |
| M5_unsupported_rate | 0.01 | 0.01 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (36)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g012 | L2 | ans→ans | O | 0.50 | 0.00 | — |
| g013 | L2 | ans→ans | O | 0.00 | 0.17 | — |
| g018 | L2 | ans→ans | O | 0.67 | 0.00 | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| g024 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g029 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | — | — | — |
| g036 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.10 | — |
| l5a02 | L5a | ans→ans | O | 0.75 | 0.00 | — |
| l5a03 | L5a | ans→ans | O | 0.67 | 0.00 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | — | — | — |
| l5a05 | L5a | ans→ans | X | 0.33 | 0.00 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.00 | — |
| l5b01 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | — | — | — |
| l5b03 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b04 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b05 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b06 | L5b | ans→ans | O | 0.33 | 0.00 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.00 | — |
| n01 | L3 | ans→ans | O | 0.50 | 0.11 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n08 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n17 | L4 | ans→ans | O | 0.67 | 0.00 | O |
| n20 | L4 | ans→ans | O | 1.00 | 0.25 | O |
| n23 | L4 | ans→ans | O | 0.00 | 0.00 | O |
| n24 | L4 | ans→ins(model_declined) | O | — | — | — |
| n25 | L3 | ans→ans | O | 1.00 | 0.08 | — |
| l5b07 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b08 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b09 | L5b | ans→ans | O | 0.00 | 0.00 | — |
| s07 | SUM | ans→ans | O | 0.50 | 0.00 | — |
| s08 | SUM | ans→ins(model_declined) | O | — | — | — |
