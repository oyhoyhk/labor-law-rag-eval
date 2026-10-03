# 평가 리포트: v2-qwen3-8B-r2

- 실행: 2026-10-03T18:29:25 · git `42b4504`
- 설정: {"name": "v2-qwen3-8B-r2", "strategy": "whole@Qwen3-Embedding-8B", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "hybrid": false, "fewshot_dev": false, "split": "all", "ids": "", "no_judge": false, "no_cache": true, "judge_no_cache": false, "budget": 600.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 Qwen/Qwen3-Embedding-8B@unpinned
- 비용: 생성+Judge 537.84원 · LLM 호출 289회 · 캐시 적중 0회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.830 (n=100) |
| M1_recall_any | 0.957 (n=92) |
| M1_recall_all | 0.772 (n=92) |
| M1_mrr | 0.848 (n=92) |
| M2_oos_refusal | 0.875 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.000 (n=92) |
| M3_citation_precision | 0.542 (n=92) |
| M3_citation_recall | 0.857 (n=92) |
| M4_kp_coverage | 0.912 (n=92) |
| M4_all_kp | 0.826 (n=92) |
| M4_complete | 0.826 (n=92) |
| M5_unsupported_rate | 0.052 (n=93) |
| M6_temporal_error | 0.000 (n=15) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 0.95 | 0.78 | 0.73 | 0.88 | 0.67 | 0.88 | 0.75 |
| M1_recall_any | 1.00 | 1.00 | 1.00 | 1.00 | 0.88 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.95 | 0.91 | 0.93 | 0.38 | 0.00 | — | 0.62 |
| M1_mrr | 0.87 | 0.91 | 0.97 | 0.79 | 0.73 | 0.51 | — | 0.94 |
| M2_oos_refusal | — | — | — | — | — | — | 0.88 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | — | 0.00 |
| M3_citation_precision | 0.72 | 0.51 | 0.61 | 0.55 | 0.30 | 0.52 | — | 0.45 |
| M3_citation_recall | 1.00 | 0.97 | 0.87 | 0.97 | 0.55 | 0.49 | — | 0.88 |
| M4_kp_coverage | 1.00 | 0.95 | 0.91 | 0.87 | 0.88 | 0.81 | — | 0.95 |
| M4_all_kp | 1.00 | 0.95 | 0.78 | 0.73 | 0.88 | 0.67 | — | 0.75 |
| M4_complete | 1.00 | 0.95 | 0.78 | 0.73 | 0.88 | 0.67 | — | 0.75 |
| M5_unsupported_rate | 0.01 | 0.03 | 0.04 | 0.04 | 0.11 | 0.15 | 0.00 | 0.03 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.80 | 0.86 |
| M1_recall_any | 0.93 | 0.98 |
| M1_recall_all | 0.75 | 0.79 |
| M1_mrr | 0.85 | 0.84 |
| M2_oos_refusal | 0.75 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.00 | 0.00 |
| M3_citation_precision | 0.49 | 0.58 |
| M3_citation_recall | 0.84 | 0.87 |
| M4_kp_coverage | 0.88 | 0.94 |
| M4_all_kp | 0.80 | 0.85 |
| M4_complete | 0.80 | 0.85 |
| M5_unsupported_rate | 0.06 | 0.05 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (41)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g006 | L1 | ans→ans | O | 1.00 | 0.11 | — |
| g011 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| g012 | L2 | ans→ans | O | 1.00 | 0.20 | — |
| g013 | L2 | ans→ans | O | 0.00 | 0.00 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.08 | — |
| g021 | L3 | ans→ans | O | 0.67 | 0.15 | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.29 | — |
| g024 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g027 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| g031 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| g036 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| l5a03 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a04 | L5a | ans→ans | X | 0.00 | 0.38 | — |
| l5a05 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a06 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.14 | — |
| l5b01 | L5b | ans→ans | O | 0.67 | 0.33 | — |
| l5b03 | L5b | ans→ans | X | 0.00 | 0.29 | — |
| l5b05 | L5b | ans→ans | X | 0.67 | 0.18 | — |
| l5b06 | L5b | ans→ans | X | 1.00 | 0.25 | — |
| s04 | SUM | ans→ans | O | 0.80 | 0.03 | — |
| s05 | SUM | ans→ans | O | 1.00 | 0.06 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n04 | L3 | ans→ans | O | 1.00 | 0.09 | — |
| n05 | L3 | ans→ans | O | 1.00 | 0.14 | — |
| n06 | L3 | ans→ans | O | 1.00 | 0.12 | — |
| n08 | L3 | ans→ans | O | 0.33 | 0.00 | — |
| n10 | L2 | ans→ans | O | 1.00 | 0.07 | — |
| n11 | L2 | ans→ans | O | 1.00 | 0.07 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.13 | O |
| n19 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| n20 | L4 | ans→ans | O | 1.00 | 0.12 | O |
| n23 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| n24 | L4 | ans→ans | O | 1.00 | 0.40 | O |
| n25 | L3 | ans→ans | O | 0.67 | 0.00 | — |
| n30 | OOS | ins→ans | — | — | 0.00 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.08 | — |
| l5b08 | L5b | ans→ans | O | 1.00 | 0.14 | — |
| l5b09 | L5b | ans→ans | O | 1.00 | 0.12 | — |
| s07 | SUM | ans→ans | O | 1.00 | 0.06 | — |
| s08 | SUM | ans→ans | O | 0.80 | 0.10 | — |
