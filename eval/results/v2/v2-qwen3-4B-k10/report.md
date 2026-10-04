# 평가 리포트: v2-qwen3-4B-k10

- 실행: 2026-10-03T21:04:37 · git `15e0e1d`
- 설정: {"name": "v2-qwen3-4B-k10", "strategy": "whole@Qwen3-Embedding-4B", "k": 10, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "hybrid": false, "fewshot_dev": false, "split": "all", "ids": "", "no_judge": false, "no_cache": true, "judge_no_cache": false, "budget": 1200.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 Qwen/Qwen3-Embedding-4B@unpinned
- 비용: 생성+Judge 713.34원 · LLM 호출 291회 · 캐시 적중 0회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.920 (n=100) |
| M1_recall_any | 0.989 (n=92) |
| M1_recall_all | 0.848 (n=92) |
| M1_mrr | 0.875 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.000 (n=92) |
| M3_citation_precision | 0.559 (n=92) |
| M3_citation_recall | 0.925 (n=92) |
| M4_kp_coverage | 0.960 (n=92) |
| M4_all_kp | 0.913 (n=92) |
| M4_complete | 0.913 (n=92) |
| M5_unsupported_rate | 0.048 (n=94) |
| M6_temporal_error | 0.067 (n=15) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 1.00 | 0.91 | 0.87 | 0.88 | 0.78 | 1.00 | 0.88 |
| M1_recall_any | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.89 | — | 1.00 |
| M1_recall_all | 1.00 | 1.00 | 0.96 | 1.00 | 0.50 | 0.00 | — | 1.00 |
| M1_mrr | 0.85 | 0.91 | 0.97 | 0.87 | 0.73 | 0.62 | — | 1.00 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | — | 0.00 |
| M3_citation_precision | 0.69 | 0.49 | 0.60 | 0.58 | 0.47 | 0.63 | — | 0.41 |
| M3_citation_recall | 1.00 | 0.97 | 0.91 | 1.00 | 0.81 | 0.68 | — | 1.00 |
| M4_kp_coverage | 1.00 | 1.00 | 0.97 | 0.93 | 0.97 | 0.85 | — | 0.95 |
| M4_all_kp | 1.00 | 1.00 | 0.91 | 0.87 | 0.88 | 0.78 | — | 0.88 |
| M4_complete | 1.00 | 1.00 | 0.91 | 0.87 | 0.88 | 0.78 | — | 0.88 |
| M5_unsupported_rate | 0.01 | 0.05 | 0.02 | 0.04 | 0.08 | 0.18 | 0.00 | 0.02 |
| M6_temporal_error | — | — | — | 0.07 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.93 | 0.91 |
| M1_recall_any | 0.97 | 1.00 |
| M1_recall_all | 0.88 | 0.83 |
| M1_mrr | 0.85 | 0.90 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.00 | 0.00 |
| M3_citation_precision | 0.51 | 0.59 |
| M3_citation_recall | 0.92 | 0.93 |
| M4_kp_coverage | 0.96 | 0.96 |
| M4_all_kp | 0.93 | 0.90 |
| M4_complete | 0.93 | 0.90 |
| M5_unsupported_rate | 0.06 | 0.04 |
| M6_temporal_error | 0.00 | 0.12 |

## 확인이 필요한 문항 (36)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g006 | L1 | ans→ans | O | 1.00 | 0.08 | — |
| g011 | L2 | ans→ans | O | 1.00 | 0.22 | — |
| g012 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.17 | — |
| g021 | L3 | ans→ans | O | 0.67 | 0.07 | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.12 | — |
| g031 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| g033 | L4 | ans→ans | O | 1.00 | 0.17 | O |
| g037 | L4 | ans→ans | O | 1.00 | 0.12 | X |
| l5a02 | L5a | ans→ans | O | 1.00 | 0.06 | — |
| l5a04 | L5a | ans→ans | O | 0.75 | 0.14 | — |
| l5a05 | L5a | ans→ans | O | 1.00 | 0.09 | — |
| l5a06 | L5a | ans→ans | O | 1.00 | 0.08 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.14 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.09 | — |
| l5b01 | L5b | ans→ans | O | 0.67 | 0.17 | — |
| l5b03 | L5b | ans→ans | O | 1.00 | 0.18 | — |
| l5b05 | L5b | ans→ans | O | 1.00 | 0.09 | — |
| l5b06 | L5b | ans→ans | X | 0.00 | 1.00 | — |
| s01 | SUM | ans→ans | O | 1.00 | 0.07 | — |
| s04 | SUM | ans→ans | O | 0.60 | 0.00 | — |
| s05 | SUM | ans→ans | O | 1.00 | 0.06 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n03 | L3 | ans→ans | O | 1.00 | 0.10 | — |
| n06 | L3 | ans→ans | O | 1.00 | 0.06 | — |
| n07 | L3 | ans→ans | O | 1.00 | 0.08 | — |
| n11 | L2 | ans→ans | O | 1.00 | 0.09 | — |
| n12 | L2 | ans→ans | O | 1.00 | 0.17 | — |
| n16 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.06 | O |
| n20 | L4 | ans→ans | O | 1.00 | 0.17 | O |
| n23 | L4 | ans→ans | O | 0.50 | 0.09 | O |
| n25 | L3 | ans→ans | O | 1.00 | 0.06 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.07 | — |
| l5b09 | L5b | ans→ans | O | 1.00 | 0.09 | — |
| s08 | SUM | ans→ans | O | 1.00 | 0.05 | — |
