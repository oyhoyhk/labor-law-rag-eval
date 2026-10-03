# 평가 리포트: v2-qwen3-8B

- 실행: 2026-10-03T16:49:23 · git `da4c24f`
- 설정: {"name": "v2-qwen3-8B", "strategy": "whole@Qwen3-Embedding-8B", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "hybrid": false, "fewshot_dev": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 600.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 Qwen/Qwen3-Embedding-8B@unpinned
- 비용: 생성+Judge 501.01원 · LLM 호출 264회 · 캐시 적중 21회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.810 (n=100) |
| M1_recall_any | 0.957 (n=92) |
| M1_recall_all | 0.772 (n=92) |
| M1_mrr | 0.848 (n=92) |
| M2_oos_refusal | 0.875 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.022 (n=92) |
| M3_citation_precision | 0.520 (n=90) |
| M3_citation_recall | 0.847 (n=92) |
| M4_kp_coverage | 0.891 (n=92) |
| M4_all_kp | 0.822 (n=90) |
| M4_complete | 0.804 (n=92) |
| M5_unsupported_rate | 0.051 (n=91) |
| M6_temporal_error | 0.067 (n=15) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 0.95 | 0.74 | 0.87 | 0.88 | 0.44 | 0.88 | 0.62 |
| M1_recall_any | 1.00 | 1.00 | 1.00 | 1.00 | 0.88 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.95 | 0.91 | 0.93 | 0.38 | 0.00 | — | 0.62 |
| M1_mrr | 0.87 | 0.91 | 0.97 | 0.79 | 0.73 | 0.51 | — | 0.94 |
| M2_oos_refusal | — | — | — | — | — | — | 0.88 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.22 | — | 0.00 |
| M3_citation_precision | 0.72 | 0.43 | 0.58 | 0.53 | 0.32 | 0.57 | — | 0.46 |
| M3_citation_recall | 1.00 | 0.97 | 0.83 | 0.97 | 0.59 | 0.46 | — | 0.88 |
| M4_kp_coverage | 1.00 | 0.95 | 0.87 | 0.93 | 0.88 | 0.63 | — | 0.92 |
| M4_all_kp | 1.00 | 0.95 | 0.74 | 0.87 | 0.88 | 0.57 | — | 0.62 |
| M4_complete | 1.00 | 0.95 | 0.74 | 0.87 | 0.88 | 0.44 | — | 0.62 |
| M5_unsupported_rate | 0.00 | 0.08 | 0.03 | 0.04 | 0.07 | 0.11 | 0.00 | 0.06 |
| M6_temporal_error | — | — | — | 0.07 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.73 | 0.88 |
| M1_recall_any | 0.93 | 0.98 |
| M1_recall_all | 0.75 | 0.79 |
| M1_mrr | 0.85 | 0.84 |
| M2_oos_refusal | 0.75 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.05 | 0.00 |
| M3_citation_precision | 0.50 | 0.54 |
| M3_citation_recall | 0.83 | 0.86 |
| M4_kp_coverage | 0.82 | 0.94 |
| M4_all_kp | 0.76 | 0.86 |
| M4_complete | 0.72 | 0.86 |
| M5_unsupported_rate | 0.04 | 0.06 |
| M6_temporal_error | 0.00 | 0.12 |

## 확인이 필요한 문항 (48)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g012 | L2 | ans→ans | O | 1.00 | 0.20 | — |
| g013 | L2 | ans→ans | O | 0.00 | 0.00 | — |
| g017 | L2 | ans→ans | O | 1.00 | 0.20 | — |
| g018 | L2 | ans→ans | O | 1.00 | 0.11 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| g021 | L3 | ans→ans | O | 1.00 | 0.11 | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g024 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g028 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g029 | L3 | ans→ans | O | 0.00 | 0.00 | — |
| g030 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| g034 | L4 | ans→ans | O | 1.00 | 0.09 | O |
| g041 | OOS | ins→ans | — | — | 0.00 | — |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a04 | L5a | ans→ans | X | 0.00 | 0.00 | — |
| l5a05 | L5a | ans→ans | O | 1.00 | 0.25 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.11 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.09 | — |
| l5b01 | L5b | ans→ans | O | 0.67 | 0.33 | — |
| l5b03 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b05 | L5b | ans→ans | X | 0.33 | 0.08 | — |
| l5b06 | L5b | ans→ins(no_valid_citation) | X | 0.00 | — | — |
| s01 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s02 | SUM | ans→ans | O | 1.00 | 0.08 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.00 | — |
| s05 | SUM | ans→ans | O | 1.00 | 0.07 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.10 | — |
| n03 | L3 | ans→ans | O | 1.00 | 0.12 | — |
| n04 | L3 | ans→ans | O | 1.00 | 0.10 | — |
| n08 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| n10 | L2 | ans→ans | O | 1.00 | 0.07 | — |
| n11 | L2 | ans→ans | O | 1.00 | 0.17 | — |
| n12 | L2 | ans→ans | O | 1.00 | 0.22 | — |
| n13 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| n14 | L2 | ans→ans | O | 1.00 | 0.10 | — |
| n16 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n20 | L4 | ans→ans | O | 1.00 | 0.17 | X |
| n22 | L4 | ans→ans | O | 1.00 | 0.22 | O |
| n23 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| n25 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.07 | — |
| l5b08 | L5b | ans→ans | O | 0.67 | 0.12 | — |
| l5b09 | L5b | ans→ans | O | 1.00 | 0.14 | — |
| s06 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s07 | SUM | ans→ans | O | 0.75 | 0.08 | — |
| s08 | SUM | ans→ans | O | 0.80 | 0.19 | — |
