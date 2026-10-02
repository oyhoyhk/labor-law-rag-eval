# 평가 리포트: v2-reverse-refs

- 실행: 2026-10-02T23:47:37 · git `b2c8efd` (dirty)
- 설정: {"name": "v2-reverse-refs", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": false, "reverse_refs": true, "prompt": "gen-v1", "precedents": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 400.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 29.55원 · LLM 호출 19회 · 캐시 적중 246회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.924 (n=92) |
| M1_recall_all | 0.696 (n=92) |
| M1_mrr | 0.799 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.098 (n=92) |
| M3_citation_precision | 0.703 (n=83) |
| M3_citation_recall | 0.856 (n=83) |
| M4_kp_coverage | 0.885 (n=83) |
| M4_all_kp | 0.747 (n=83) |
| M4_complete | 0.674 (n=92) |
| M5_unsupported_rate | 0.018 (n=83) |
| M6_temporal_error | 0.071 (n=14) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 0.95 | 1.00 | 0.93 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.84 | 0.87 | 0.87 | 0.12 | 0.00 | — | 0.50 |
| M1_mrr | 0.95 | 0.73 | 0.95 | 0.77 | 0.75 | 0.46 | — | 0.84 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.04 | 0.07 | 0.12 | 0.67 | — | 0.00 |
| M3_citation_precision | 0.72 | 0.81 | 0.77 | 0.73 | 0.54 | 0.61 | — | 0.38 |
| M3_citation_recall | 1.00 | 0.97 | 0.86 | 0.89 | 0.60 | 0.42 | — | 0.70 |
| M4_kp_coverage | 1.00 | 0.96 | 0.91 | 0.87 | 0.87 | 0.33 | — | 0.73 |
| M4_all_kp | 1.00 | 0.90 | 0.77 | 0.79 | 0.57 | 0.00 | — | 0.38 |
| M4_complete | 1.00 | 0.90 | 0.74 | 0.73 | 0.50 | 0.00 | — | 0.38 |
| M5_unsupported_rate | 0.00 | 0.00 | 0.01 | 0.07 | 0.04 | 0.06 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.07 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 0.95 | 0.90 |
| M1_recall_all | 0.68 | 0.71 |
| M1_mrr | 0.82 | 0.78 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.10 | 0.10 |
| M3_citation_precision | 0.68 | 0.72 |
| M3_citation_recall | 0.85 | 0.86 |
| M4_kp_coverage | 0.87 | 0.90 |
| M4_all_kp | 0.69 | 0.79 |
| M4_complete | 0.62 | 0.71 |
| M5_unsupported_rate | 0.02 | 0.01 |
| M6_temporal_error | 0.14 | 0.00 |

## 확인이 필요한 문항 (36)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g018 | L2 | ans→ans | O | 0.67 | 0.00 | — |
| g019 | L2 | ans→ans | O | 0.67 | 0.00 | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| g027 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g030 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | — | — | — |
| g037 | L4 | ans→ans | O | 1.00 | 0.33 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a02 | L5a | ans→ans | O | 0.75 | 0.00 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | — | — | — |
| l5a05 | L5a | ans→ans | X | 0.67 | 0.00 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.09 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.07 | — |
| l5b01 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b02 | L5b | ans→ins(retrieval_below_tau) | O | — | — | — |
| l5b03 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b04 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b05 | L5b | ans→ans | O | 0.33 | 0.00 | — |
| l5b06 | L5b | ans→ans | O | 0.67 | 0.17 | — |
| s03 | SUM | ans→ans | O | 0.75 | 0.00 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.00 | — |
| n01 | L3 | ans→ins(model_declined) | O | — | — | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n04 | L3 | ans→ans | O | 1.00 | 0.12 | — |
| n08 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n17 | L4 | ans→ans | O | 0.67 | 0.00 | O |
| n18 | L4 | ans→ans | O | 1.00 | 0.08 | O |
| n23 | L4 | ans→ans | O | 0.00 | 0.00 | O |
| n24 | L4 | ans→ans | O | 0.50 | 0.50 | X |
| l5b07 | L5b | ans→ins(model_declined) | O | — | — | — |
| l5b08 | L5b | ans→ins(model_declined) | X | — | — | — |
| l5b09 | L5b | ans→ans | O | 0.00 | 0.00 | — |
| s07 | SUM | ans→ans | O | 0.75 | 0.00 | — |
| s08 | SUM | ans→ans | O | 0.20 | 0.00 | — |
