# 평가 리포트: exp-k10

- 실행: 2026-10-02T11:04:48 · git `d84a500`
- 설정: {"name": "exp-k10", "strategy": "article", "k": 10, "tau": 0.5, "no_inject": false, "no_links": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 300.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 265.15원 · LLM 호출 153회 · 캐시 적중 5회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.965 (n=57) |
| M1_recall_all | 0.860 (n=57) |
| M1_mrr | 0.796 (n=57) |
| M2_oos_refusal | 1.000 (n=4) |
| M2_l5b_no_assertion | 1.000 (n=6) |
| M2_over_refusal | 0.078 (n=51) |
| M3_citation_precision | 0.730 (n=49) |
| M3_citation_recall | 0.937 (n=49) |
| M4_kp_coverage | 0.956 (n=47) |
| M4_all_kp | 0.872 (n=47) |
| M5_unsupported_rate | 0.038 (n=49) |
| M6_temporal_error | 0.000 (n=5) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 1.00 | 1.00 | 0.86 | 0.88 | 1.00 | — | 1.00 |
| M1_recall_all | 1.00 | 0.91 | 1.00 | 0.86 | 0.50 | 0.67 | — | 1.00 |
| M1_mrr | 0.95 | 0.74 | 0.93 | 0.79 | 0.76 | 0.52 | — | 0.74 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | 1.00 | — | — |
| M2_over_refusal | 0.00 | 0.09 | 0.00 | 0.29 | 0.12 | — | — | 0.00 |
| M3_citation_precision | 0.72 | 0.74 | 0.97 | 1.00 | 0.56 | 0.38 | — | 0.36 |
| M3_citation_recall | 1.00 | 1.00 | 0.90 | 1.00 | 0.70 | 1.00 | — | 1.00 |
| M4_kp_coverage | 1.00 | 0.97 | 0.88 | 1.00 | 0.92 | — | — | 1.00 |
| M4_all_kp | 1.00 | 0.90 | 0.70 | 1.00 | 0.71 | — | — | 1.00 |
| M5_unsupported_rate | 0.00 | 0.01 | 0.00 | 0.17 | 0.12 | 0.04 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 1.00 | 0.94 |
| M1_recall_all | 0.86 | 0.86 |
| M1_mrr | 0.81 | 0.79 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | 1.00 | 1.00 |
| M2_over_refusal | 0.15 | 0.03 |
| M3_citation_precision | 0.70 | 0.75 |
| M3_citation_recall | 0.94 | 0.93 |
| M4_kp_coverage | 0.96 | 0.96 |
| M4_all_kp | 0.88 | 0.87 |
| M5_unsupported_rate | 0.02 | 0.05 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (16)

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
| l5a02 | L5a | ans→ans | O | 0.75 | 0.25 | — |
| l5a04 | L5a | ans→ins(model_declined) | O | — | — | — |
| l5a05 | L5a | ans→ans | X | 0.67 | 0.20 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.14 | — |
| l5b05 | L5b | ins→ans | O | — | 0.08 | — |
