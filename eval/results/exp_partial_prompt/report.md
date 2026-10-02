# 평가 리포트: exp-partial-prompt

- 실행: 2026-10-02T11:13:53 · git `f5b80ef`
- 설정: {"name": "exp-partial-prompt", "strategy": "article", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "prompt": "gen-v2-partial", "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 300.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 nlpai-lab/KURE-v1@8b418a58
- 비용: 생성+Judge 123.26원 · LLM 호출 101회 · 캐시 적중 65회

## 전체

| 지표 | 값 |
|---|---|
| M1_recall_any | 0.895 (n=57) |
| M1_recall_all | 0.702 (n=57) |
| M1_mrr | 0.786 (n=57) |
| M2_oos_refusal | 1.000 (n=4) |
| M2_l5b_no_assertion | 1.000 (n=6) |
| M2_over_refusal | 0.039 (n=51) |
| M3_citation_precision | 0.704 (n=53) |
| M3_citation_recall | 0.844 (n=53) |
| M4_kp_coverage | 0.879 (n=49) |
| M4_all_kp | 0.776 (n=49) |
| M5_unsupported_rate | 0.020 (n=53) |
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
| M3_citation_precision | 0.72 | 0.71 | 0.93 | 1.00 | 0.49 | 0.46 | — | 0.33 |
| M3_citation_recall | 1.00 | 0.95 | 0.80 | 1.00 | 0.49 | 0.75 | — | 0.77 |
| M4_kp_coverage | 0.95 | 0.85 | 0.90 | 1.00 | 0.73 | — | — | 0.83 |
| M4_all_kp | 0.90 | 0.82 | 0.80 | 1.00 | 0.43 | — | — | 0.60 |
| M5_unsupported_rate | 0.00 | 0.05 | 0.02 | 0.00 | 0.04 | 0.00 | — | 0.00 |
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
| M3_citation_precision | 0.71 | 0.70 |
| M3_citation_recall | 0.88 | 0.82 |
| M4_kp_coverage | 0.87 | 0.88 |
| M4_all_kp | 0.74 | 0.80 |
| M5_unsupported_rate | 0.04 | 0.01 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (19)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g003 | L1 | ans→ans | O | 0.50 | 0.00 | — |
| g013 | L2 | ans→ans | O | 0.00 | 0.11 | — |
| g016 | L2 | ans→ans | O | 1.00 | 0.33 | — |
| g018 | L2 | ans→ans | O | 0.33 | 0.00 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.10 | — |
| g042 | L2 | ans→ans | X | 1.00 | 0.00 | — |
| g021 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.20 | — |
| g024 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ins(model_declined) | X | — | — | — |
| l5a02 | L5a | ans→ans | O | 0.75 | 0.00 | — |
| l5a03 | L5a | ans→ans | O | 0.33 | 0.00 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | — | — | — |
| l5a05 | L5a | ans→ans | X | 0.33 | 0.20 | — |
| l5a06 | L5a | ans→ans | O | 0.67 | 0.11 | — |
| l5b01 | L5b | ins→ans | X | — | 0.00 | — |
| l5b03 | L5b | ins→ins(model_declined) | X | — | — | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.33 | 0.00 | — |
