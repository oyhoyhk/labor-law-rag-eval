# 평가 리포트: v2-qwen3-4B

- 실행: 2026-10-03T16:45:21 · git `da4c24f`
- 설정: {"name": "v2-qwen3-4B", "strategy": "whole@Qwen3-Embedding-4B", "k": 5, "tau": 0.5, "no_inject": false, "no_links": false, "siblings": true, "reverse_refs": false, "prompt": "gen-v3-precedent", "precedents": true, "hybrid": false, "fewshot_dev": false, "split": "all", "ids": "", "no_judge": false, "no_cache": false, "judge_no_cache": false, "budget": 600.0}
- 모델: openai/gpt-5.6-luna · seed 42 · temperature 0 · 임베딩 Qwen/Qwen3-Embedding-4B@unpinned
- 비용: 생성+Judge 528.26원 · LLM 호출 272회 · 캐시 적중 12회

## 전체

| 지표 | 값 |
|---|---|
| M0_accuracy | 0.870 (n=100) |
| M1_recall_any | 0.946 (n=92) |
| M1_recall_all | 0.772 (n=92) |
| M1_mrr | 0.869 (n=92) |
| M2_oos_refusal | 1.000 (n=8) |
| M2_l5b_no_assertion | — |
| M2_over_refusal | 0.033 (n=92) |
| M3_citation_precision | 0.586 (n=89) |
| M3_citation_recall | 0.859 (n=92) |
| M4_kp_coverage | 0.921 (n=92) |
| M4_all_kp | 0.888 (n=89) |
| M4_complete | 0.859 (n=92) |
| M5_unsupported_rate | 0.041 (n=90) |
| M6_temporal_error | 0.000 (n=15) |

## 단계별

| 지표 | L1 | L2 | L3 | L4 | L5a | L5b | OOS | SUM |
|---|---|---|---|---|---|---|---|---|
| M0_accuracy | 1.00 | 0.95 | 0.91 | 0.87 | 0.88 | 0.44 | 1.00 | 0.75 |
| M1_recall_any | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 | 0.67 | — | 1.00 |
| M1_recall_all | 1.00 | 0.95 | 0.96 | 0.93 | 0.25 | 0.00 | — | 0.62 |
| M1_mrr | 0.85 | 0.91 | 0.97 | 0.87 | 0.69 | 0.58 | — | 1.00 |
| M2_oos_refusal | — | — | — | — | — | — | 1.00 | — |
| M2_l5b_no_assertion | — | — | — | — | — | — | — | — |
| M2_over_refusal | 0.00 | 0.00 | 0.00 | 0.00 | 0.12 | 0.22 | — | 0.00 |
| M3_citation_precision | 0.71 | 0.61 | 0.61 | 0.61 | 0.33 | 0.67 | — | 0.41 |
| M3_citation_recall | 1.00 | 0.97 | 0.89 | 0.97 | 0.51 | 0.50 | — | 0.86 |
| M4_kp_coverage | 1.00 | 0.97 | 0.96 | 0.93 | 0.88 | 0.67 | — | 0.88 |
| M4_all_kp | 1.00 | 0.95 | 0.91 | 0.87 | 1.00 | 0.57 | — | 0.75 |
| M4_complete | 1.00 | 0.95 | 0.91 | 0.87 | 0.88 | 0.44 | — | 0.75 |
| M5_unsupported_rate | 0.00 | 0.04 | 0.04 | 0.01 | 0.13 | 0.10 | 0.09 | 0.03 |
| M6_temporal_error | — | — | — | 0.00 | — | — | — | — |

## 분할별

| 지표 | dev | test |
|---|---|---|
| M0_accuracy | 0.86 | 0.88 |
| M1_recall_any | 0.93 | 0.96 |
| M1_recall_all | 0.80 | 0.75 |
| M1_mrr | 0.84 | 0.89 |
| M2_oos_refusal | 1.00 | 1.00 |
| M2_l5b_no_assertion | — | — |
| M2_over_refusal | 0.07 | 0.00 |
| M3_citation_precision | 0.57 | 0.60 |
| M3_citation_recall | 0.85 | 0.86 |
| M4_kp_coverage | 0.89 | 0.95 |
| M4_all_kp | 0.92 | 0.86 |
| M4_complete | 0.85 | 0.86 |
| M5_unsupported_rate | 0.03 | 0.05 |
| M6_temporal_error | 0.00 | 0.00 |

## 확인이 필요한 문항 (38)

| id | 단계 | 기대→실제 | 검색 | 정답 포인트 | 근거 없는 주장 | 시점 오류 |
|---|---|---|---|---|---|---|
| g011 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| g012 | L2 | ans→ans | O | 1.00 | 0.14 | — |
| g020 | L2 | ans→ans | O | 1.00 | 0.12 | — |
| g021 | L3 | ans→ans | O | 1.00 | 0.08 | — |
| g023 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g025 | L3 | ans→ans | O | 1.00 | 0.17 | — |
| g027 | L3 | ans→ans | O | 1.00 | 0.12 | — |
| g029 | L3 | ans→ans | O | 0.50 | 0.00 | — |
| g034 | L4 | ans→ans | O | 1.00 | 0.07 | O |
| g036 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| g041 | OOS | ins→ans | — | — | 0.09 | — |
| l5a01 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5a02 | L5a | ans→ans | O | 1.00 | 0.07 | — |
| l5a03 | L5a | ans→ans | X | 1.00 | 0.38 | — |
| l5a04 | L5a | ans→ins(model_declined) | X | 0.00 | — | — |
| l5a05 | L5a | ans→ans | O | 1.00 | 0.09 | — |
| l5a07 | L5a | ans→ans | O | 1.00 | 0.11 | — |
| l5a08 | L5a | ans→ans | O | 1.00 | 0.12 | — |
| l5b01 | L5b | ans→ans | O | 0.67 | 0.12 | — |
| l5b03 | L5b | ans→ins(model_declined) | X | 0.00 | — | — |
| l5b05 | L5b | ans→ans | X | 0.67 | 0.07 | — |
| l5b06 | L5b | ans→ins(no_valid_citation) | X | 0.00 | — | — |
| s01 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s05 | SUM | ans→ans | O | 0.67 | 0.06 | — |
| n02 | L3 | ans→ans | O | 0.67 | 0.07 | — |
| n09 | L2 | ans→ans | O | 0.50 | 0.00 | — |
| n11 | L2 | ans→ans | O | 1.00 | 0.15 | — |
| n15 | L2 | ans→ans | O | 1.00 | 0.17 | — |
| n18 | L4 | ans→ans | O | 1.00 | 0.13 | O |
| n23 | L4 | ans→ans | O | 0.50 | 0.00 | O |
| n25 | L3 | ans→ans | O | 1.00 | 0.05 | — |
| n29 | L3 | ans→ans | O | 1.00 | 0.14 | — |
| l5b07 | L5b | ans→ans | O | 1.00 | 0.18 | — |
| l5b08 | L5b | ans→ans | O | 0.67 | 0.22 | — |
| l5b09 | L5b | ans→ans | O | 1.00 | 0.12 | — |
| s06 | SUM | ans→ans | O | 1.00 | 0.03 | — |
| s07 | SUM | ans→ans | O | 1.00 | 0.08 | — |
| s08 | SUM | ans→ans | O | 0.40 | 0.05 | — |
