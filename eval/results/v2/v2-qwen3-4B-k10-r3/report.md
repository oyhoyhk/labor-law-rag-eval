# 평가 리포트: v2-qwen3-4B-k10-r3

- 실행: 2026-10-03T21:14:29 · git `15e0e1d`
- 설정: {"name": "v2-qwen3-4B-k10-r3", "strategy": "whole@Qwen3-Embedding-4B", "k": 10, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "hybrid": false, "fewshot_dev": false, "split": "all", "ids": "", "no_judge": false, "no_cache": true, "judge_no_cache": false, "budget": 1200.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 Qwen/Qwen3-Embedding-4B@unpinned
- 비용: 생성+Judge 427.27원 · LLM 호출 290회 · 캐시 적중 0회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.930 (n=100) |
| M1_recall_any | 0.989 (n=92) |
| M1_recall_all | 0.848 (n=92) |
| M1_mrr | 0.875 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.000 (n=92) |
| M3_citation_precision | 0.548 (n=92) |
| M3_citation_recall | 0.909 (n=92) |
| M4_kp_coverage | 0.970 (n=92) |
| M4_all_kp | 0.924 (n=92) |
| M4_complete | 0.924 (n=92) |
| M5_unsupported_rate | 0.037 (n=93) |
| M6_temporal_error | 0.067 (n=15) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 0.90 | 1.00 | 0.87 | 0.93 | 0.88 | 0.89 | 1.00 | 1.00 |
| M1_recall_any | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.89 | — | 1.00 |
| M1_recall_all | 1.00 | 1.00 | 0.96 | 1.00 | 0.50 | 0.00 | — | 1.00 |
| M1_mrr | 0.85 | 0.91 | 0.97 | 0.87 | 0.73 | 0.62 | — | 1.00 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | — | 0.00 |
| M3_citation_precision | 0.70 | 0.49 | 0.60 | 0.46 | 0.50 | 0.69 | — | 0.38 |
| M3_citation_recall | 1.00 | 0.97 | 0.88 | 0.97 | 0.81 | 0.66 | — | 1.00 |
| M4_kp_coverage | 0.95 | 1.00 | 0.95 | 0.97 | 0.97 | 0.96 | — | 1.00 |
| M4_all_kp | 0.90 | 1.00 | 0.87 | 0.93 | 0.88 | 0.89 | — | 1.00 |
| M4_complete | 0.90 | 1.00 | 0.87 | 0.93 | 0.88 | 0.89 | — | 1.00 |
| M5_unsupported_rate | 0.01 | 0.05 | 0.01 | 0.04 | 0.07 | 0.09 | 0.00 | 0.02 |
| M6_temporal_error | — | — | — | 0.07 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.93 | 0.93 |
| M1_recall_any | 0.97 | 1.00 |
| M1_recall_all | 0.88 | 0.83 |
| M1_mrr | 0.85 | 0.90 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.00 | 0.00 |
| M3_citation_precision | 0.51 | 0.58 |
| M3_citation_recall | 0.89 | 0.92 |
| M4_kp_coverage | 0.97 | 0.97 |
| M4_all_kp | 0.93 | 0.92 |
| M4_complete | 0.93 | 0.92 |
| M5_unsupported_rate | 0.03 | 0.04 |
| M6_temporal_error | 0.00 | 0.12 |

## 확인이 필요한 문항 (34)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g003 | L1 | ans→ans | O | 0.50 | 0.00 | — |
| g006 | L1 | ans→ans | O | 1.00 | 0.08 | — |
| g011 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.17 | — |
| g021 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g029 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| g034 | L4 | ans→ans | O | 1.00 | 0.07 | O |
| g037 | L4 | ans→ans | O | 1.00 | 0.09 | X |
| l5a02 | L5a | ans→ans | O | 1.00 | 0.08 | — |
| l5a04 | L5a | ans→ans | O | 0.75 | 0.14 | — |
| l5a05 | L5a | ans→ans | O | 1.00 | 0.10 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.14 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.10 | — |
| l5b01 | L5b | ans→ans | O | 1.00 | 0.12 | — |
| l5b05 | L5b | ans→ans | O | 1.00 | 0.09 | — |
| l5b06 | L5b | ans→ans | X | 0.67 | 0.36 | — |
| s01 | SUM | ans→ans | O | 1.00 | 0.06 | — |
| s05 | SUM | ans→ans | O | 1.00 | 0.05 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.08 | — |
| n06 | L3 | ans→ans | O | 1.00 | 0.11 | — |
| n08 | L3 | ans→ans | O | 1.00 | 0.05 | — |
| n11 | L2 | ans→ans | O | 1.00 | 0.10 | — |
| n12 | L2 | ans→ans | O | 1.00 | 0.11 | — |
| n13 | L2 | ans→ans | O | 1.00 | 0.22 | — |
| n14 | L2 | ans→ans | O | 1.00 | 0.17 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n20 | L4 | ans→ans | O | 1.00 | 0.11 | O |
| n21 | L4 | ans→ans | O | 1.00 | 0.14 | O |
| n23 | L4 | ans→ans | O | 0.50 | 0.09 | O |
| n25 | L3 | ans→ans | O | 1.00 | 0.05 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.07 | — |
| l5b08 | L5b | ans→ans | O | 1.00 | 0.12 | — |
| s06 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s08 | SUM | ans→ans | O | 1.00 | 0.05 | — |
