# 평가 리포트: baseline-v1.1

- 실행: 2026-10-02T10:54:42 · git `889eb06` (dirty)
- 설정: {"name": "baseline-v1.1", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 200.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 2.43원 · LLM 호출 1회 · 캐시 적중 162회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.895 (n=57) |
| M1_recall_all | 0.702 (n=57) |
| M1_mrr | 0.786 (n=57) |
| M2_oos_refusal | 1.000 (n=4) |
| M2_l5b_no_assertion | 1.000 (n=6) |
| M2_over_refusal | 0.039 (n=51) |
| M3_citation_precision | 0.716 (n=51) |
| M3_citation_recall | 0.874 (n=51) |
| M4_kp_coverage | 0.904 (n=49) |
| M4_all_kp | 0.776 (n=49) |
| M5_unsupported_rate | 0.029 (n=51) |
| M6_temporal_error | 0.000 (n=6) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 0.91 | 1.00 | 0.86 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.73 | 0.90 | 0.86 | 0.12 | 0.50 | — | 0.60 |
| M1_mrr | 0.95 | 0.73 | 0.93 | 0.79 | 0.75 | 0.47 | — | 0.74 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | 1.00 | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.14 | 0.12 | — | — | 0.00 |
| M3_citation_precision | 0.78 | 0.69 | 0.92 | 1.00 | 0.51 | 0.42 | — | 0.32 |
| M3_citation_recall | 1.00 | 0.95 | 0.85 | 1.00 | 0.53 | 1.00 | — | 0.77 |
| M4_kp_coverage | 1.00 | 0.88 | 0.90 | 1.00 | 0.82 | — | — | 0.78 |
| M4_all_kp | 1.00 | 0.82 | 0.80 | 1.00 | 0.43 | — | — | 0.40 |
| M5_unsupported_rate | 0.00 | 0.03 | 0.00 | 0.06 | 0.10 | 0.08 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 0.91 | 0.89 |
| M1_recall_all | 0.73 | 0.69 |
| M1_mrr | 0.80 | 0.78 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | 1.00 | 1.00 |
| M2_over_refusal | 0.05 | 0.03 |
| M3_citation_precision | 0.70 | 0.73 |
| M3_citation_recall | 0.88 | 0.87 |
| M4_kp_coverage | 0.89 | 0.91 |
| M4_all_kp | 0.74 | 0.80 |
| M5_unsupported_rate | 0.03 | 0.03 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (20)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g013 | L2 | ans→ans | O | 0.00 | 0.29 | — |
| g019 | L2 | ans→ans | O | 0.67 | 0.00 | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| g030 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | — | — | — |
| g037 | L4 | ans→ans | O | 1.00 | 0.33 | O |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a02 | L5a | ans→ans | O | 0.75 | 0.00 | — |
| l5a03 | L5a | ans→ans | O | 0.67 | 0.40 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | — | — | — |
| l5a05 | L5a | ans→ans | X | 0.67 | 0.00 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.09 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.07 | — |
| l5b01 | L5b | ins→ins(model_declined) | X | — | — | — |
| l5b03 | L5b | ins→ins(model_declined) | X | — | — | — |
| l5b06 | L5b | ins→ans | O | — | 0.17 | — |
| s03 | SUM | ans→ans | O | 0.75 | 0.00 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.00 | — |
