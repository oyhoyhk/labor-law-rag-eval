# 평가 리포트: exp-h1-fixed

- 실행: 2026-10-02T11:04:45 · git `d84a500`
- 설정: {"name": "exp-h1-fixed", "strategy": "fixed", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 300.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 250.76원 · LLM 호출 149회 · 캐시 적중 2회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.895 (n=57) |
| M1_recall_all | 0.684 (n=57) |
| M1_mrr | 0.796 (n=57) |
| M2_oos_refusal | 1.000 (n=4) |
| M2_l5b_no_assertion | 1.000 (n=6) |
| M2_over_refusal | 0.157 (n=51) |
| M3_citation_precision | 0.342 (n=45) |
| M3_citation_recall | 0.905 (n=45) |
| M4_kp_coverage | 0.916 (n=43) |
| M4_all_kp | 0.767 (n=43) |
| M5_unsupported_rate | 0.050 (n=45) |
| M6_temporal_error | 0.333 (n=6) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M1_recall_any | 1.00 | 0.73 | 1.00 | 0.86 | 0.75 | 1.00 | — | 1.00 |
| M1_recall_all | 1.00 | 0.64 | 0.90 | 0.86 | 0.12 | 0.50 | — | 0.60 |
| M1_mrr | 0.93 | 0.67 | 0.95 | 0.86 | 0.60 | 0.76 | — | 0.77 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | 1.00 | — | — |
| M2_over_refusal | 0.00 | 0.27 | 0.20 | 0.14 | 0.25 | — | — | 0.00 |
| M3_citation_precision | 0.37 | 0.39 | 0.46 | 0.39 | 0.19 | 0.42 | — | 0.13 |
| M3_citation_recall | 1.00 | 1.00 | 0.94 | 1.00 | 0.57 | 1.00 | — | 0.77 |
| M4_kp_coverage | 1.00 | 1.00 | 0.88 | 0.92 | 0.74 | — | — | 0.89 |
| M4_all_kp | 1.00 | 1.00 | 0.62 | 0.83 | 0.33 | — | — | 0.60 |
| M5_unsupported_rate | 0.00 | 0.01 | 0.03 | 0.10 | 0.14 | 0.25 | — | 0.00 |
| M6_temporal_error | — | — | — | 0.33 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M1_recall_any | 0.91 | 0.89 |
| M1_recall_all | 0.73 | 0.66 |
| M1_mrr | 0.83 | 0.77 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | 1.00 | 1.00 |
| M2_over_refusal | 0.10 | 0.19 |
| M3_citation_precision | 0.39 | 0.31 |
| M3_citation_recall | 0.92 | 0.89 |
| M4_kp_coverage | 0.94 | 0.90 |
| M4_all_kp | 0.78 | 0.76 |
| M5_unsupported_rate | 0.04 | 0.06 |
| M6_temporal_error | 0.33 | 0.33 |

## 확인이 필요한 문항 (27)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g013 | L2 | ans→ins(model_declined) | X | — | — | — |
| g014 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g017 | L2 | ans→ins(model_declined) | O | — | — | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.10 | — |
| g042 | L2 | ans→ins(model_declined) | X | — | — | — |
| g021 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g022 | L3 | ans→ins(model_declined) | O | — | — | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.25 | — |
| g024 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g027 | L3 | ans→ins(model_declined) | O | — | — | — |
| g028 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | — | — | — |
| g032 | L4 | ans→ans | O | 1.00 | 0.25 | O |
| g033 | L4 | ans→ans | O | 1.00 | 0.00 | X |
| g036 | L4 | ans→ans | O | 0.50 | 0.00 | X |
| g037 | L4 | ans→ans | O | 1.00 | 0.33 | O |
| l5a01 | L5a | ans→ans | O | 0.33 | 0.14 | — |
| l5a02 | L5a | ans→ans | O | 0.75 | 0.00 | — |
| l5a03 | L5a | ans→ans | O | 0.67 | 0.20 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | — | — | — |
| l5a05 | L5a | ans→ins(no_valid_citation) | X | — | — | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.00 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.40 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.09 | — |
| l5b06 | L5b | ins→ans | O | — | 0.50 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.67 | 0.00 | — |
