# 평가 리포트: v2-qwen3-4B-r3

- 실행: 2026-10-03T18:33:38 · git `42b4504`
- 설정: {"name": "v2-qwen3-4B-r3", "strategy": "whole@Qwen3-Embedding-4B", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "hybrid": false, "fewshot_dev": false, "split": "all", "ids": "", "no_judge": false, "no_cache": true, "judge_no_cache": false, "budget": 600.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 Qwen/Qwen3-Embedding-4B@unpinned
- 비용: 생성+Judge 376.76원 · LLM 호출 285회 · 캐시 적중 0회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.830 (n=100) |
| M1_recall_any | 0.946 (n=92) |
| M1_recall_all | 0.772 (n=92) |
| M1_mrr | 0.869 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.011 (n=92) |
| M3_citation_precision | 0.589 (n=91) |
| M3_citation_recall | 0.859 (n=92) |
| M4_kp_coverage | 0.893 (n=92) |
| M4_all_kp | 0.824 (n=91) |
| M4_complete | 0.815 (n=92) |
| M5_unsupported_rate | 0.048 (n=91) |
| M6_temporal_error | 0.000 (n=15) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 1.00 | 0.74 | 0.87 | 0.75 | 0.56 | 1.00 | 0.62 |
| M1_recall_any | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.95 | 0.96 | 0.93 | 0.25 | 0.00 | — | 0.62 |
| M1_mrr | 0.85 | 0.91 | 0.97 | 0.87 | 0.69 | 0.58 | — | 1.00 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.11 | — | 0.00 |
| M3_citation_precision | 0.71 | 0.60 | 0.66 | 0.62 | 0.28 | 0.62 | — | 0.42 |
| M3_citation_recall | 1.00 | 0.97 | 0.91 | 0.97 | 0.51 | 0.53 | — | 0.78 |
| M4_kp_coverage | 1.00 | 1.00 | 0.86 | 0.90 | 0.83 | 0.70 | — | 0.85 |
| M4_all_kp | 1.00 | 1.00 | 0.74 | 0.87 | 0.75 | 0.62 | — | 0.62 |
| M4_complete | 1.00 | 1.00 | 0.74 | 0.87 | 0.75 | 0.56 | — | 0.62 |
| M5_unsupported_rate | 0.00 | 0.05 | 0.04 | 0.04 | 0.09 | 0.09 | — | 0.04 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.82 | 0.84 |
| M1_recall_any | 0.93 | 0.96 |
| M1_recall_all | 0.80 | 0.75 |
| M1_mrr | 0.84 | 0.89 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.03 | 0.00 |
| M3_citation_precision | 0.55 | 0.62 |
| M3_citation_recall | 0.84 | 0.88 |
| M4_kp_coverage | 0.85 | 0.92 |
| M4_all_kp | 0.82 | 0.83 |
| M4_complete | 0.80 | 0.83 |
| M5_unsupported_rate | 0.05 | 0.05 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (39)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g011 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g012 | L2 | ans→ans | O | 1.00 | 0.22 | — |
| g017 | L2 | ans→ans | O | 1.00 | 0.20 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.09 | — |
| g021 | L3 | ans→ans | O | 1.00 | 0.07 | — |
| g024 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g028 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| g029 | L3 | ans→ans | O | 0.00 | 0.50 | — |
| g031 | L4 | ans→ans | O | 0.50 | 0.20 | O |
| g034 | L4 | ans→ans | O | 1.00 | 0.08 | O |
| l5a02 | L5a | ans→ans | O | 1.00 | 0.08 | — |
| l5a03 | L5a | ans→ans | X | 0.67 | 0.20 | — |
| l5a04 | L5a | ans→ans | X | 0.00 | 0.11 | — |
| l5a05 | L5a | ans→ans | O | 1.00 | 0.10 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.14 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.11 | — |
| l5b01 | L5b | ans→ans | O | 0.67 | 0.14 | — |
| l5b03 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b05 | L5b | ans→ans | X | 0.67 | 0.19 | — |
| l5b06 | L5b | ans→ans | X | 0.00 | 0.10 | — |
| s01 | SUM | ans→ans | O | 0.75 | 0.00 | — |
| s05 | SUM | ans→ans | O | 0.67 | 0.07 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n03 | L3 | ans→ans | O | 1.00 | 0.33 | — |
| n05 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| n06 | L3 | ans→ans | O | 1.00 | 0.11 | — |
| n11 | L2 | ans→ans | O | 1.00 | 0.08 | — |
| n12 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| n13 | L2 | ans→ans | O | 1.00 | 0.10 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.14 | O |
| n20 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n23 | L4 | ans→ans | O | 0.00 | 0.00 | O |
| n24 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n25 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.08 | — |
| l5b08 | L5b | ans→ans | O | 1.00 | 0.09 | — |
| l5b09 | L5b | ans→ans | O | 1.00 | 0.14 | — |
| s07 | SUM | ans→ans | O | 1.00 | 0.08 | — |
| s08 | SUM | ans→ans | O | 0.40 | 0.13 | — |
