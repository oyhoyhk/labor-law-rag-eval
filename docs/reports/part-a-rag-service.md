# Part A 리포트: 조 전체 색인 + 조문, 판례 그래프 확장 RAG, 전체 정답률 0.717 → 0.777

> **2026-10-04 갱신**: 기본 임베딩 KURE-v1 → Qwen3-Embedding-4B(색인 `whole@Qwen3-Embedding-4B`, `make ingest`의 `--preset qwen3-4b`), 검색 top-5 → top-10. 근거 `docs/findings/2026-10-03-embedding-finetune.md`. 아래 본문의 KURE, top-5 수치는 2026-10-03 기준
> 대상: 현재 기본 구성(2026-10-03, git `a6efc0b` 이후), 근거 수치는 모두 저장소 파일에서 인용, 표마다 출처 경로 표기
> 관련: 평가 체계 [part-b-eval-harness.md](part-b-eval-harness.md), 개선 실험 [part-c-experiments.md](part-c-experiments.md), 초기 설계 [../design.md](../design.md)

## 결론

- 노동 관계 법령 24건(조문 894개)과 대법원 판례 400건을 근거로, 인용(`[S#]`)이 붙은 답변 또는 `insufficient_context`를 반환하는 FastAPI 서비스
- 기본 구성: 조 전체 색인(조 1개 = 벡터 1개), 검색 top-5, 거절 임계값 τ 0.50, 위임 확장, 판례 연결, 시행 상태 헤더 주입, 프롬프트 `gen-v3-precedent`
- 품질(GT v2.2 100문항, 3회 평균): 전체 정답률 0.717 → **0.777**, 완전 정답 0.692 → 0.768, 판례형 완전 정답 0 → **0.444(유의)**, 과잉 거절 0.105 → **0.065(유의)** (`eval/results/noise_floor.json`, `eval/results/noise_floor_final.json`, `eval/results/v2/v2-final/diff_vs_base.json`)
- 대가: 인용 정밀도 0.700 → 0.583(유의 악화), 생성 호출당 입력 토큰 3,576 → 6,075(+70%)
- 환각 방지 장치 3중: 검색 점수 게이트(LLM 미호출 거절), 프롬프트의 근거 블록 외 서술 금지와 `[정보 부족]` 규칙, 인용 검증(유효 인용 0건이면 거절로 전환)
- 시점 판단은 LLM이 아니라 인제스트 단계에서 결정적으로 산출 - 주입을 끄면 시점형 완전 정답 0.667 → 0.240(유의 악화)

## 1. 과제 요구사항 대응

| 요구사항 | 충족 위치 | 근거 파일 |
|---|---|---|
| Ingest 파이프라인 | §3 파싱 → Provision Graph → 색인 | `app/ingest/parse.py`, `app/ingest/provision.py`, `app/ingest/precedent.py`, `app/index.py`, `Makefile`(`make ingest`) |
| Chunking 전략과 근거 | §4 조 전체 색인, 3방식 실측 비교 | `app/ingest/chunk.py`, `eval/retrieval_check.py`, `eval/results/v2/v2-h1-fixed/diff_vs_base.json` |
| Embedding, Index | §3.3 KURE-v1 + FAISS `IndexFlatIP` | `app/index.py`, `data/index/*/meta.json` |
| 질의 검색 + 답변 API | §5, §9 `POST /v1/query` | `app/rag.py`, `app/api.py` |
| 출처 인용(Citation) | §8 인용 검증, 근거 문장 추출, 원문 링크 | `app/rag.py` `finalize()` |
| Request/Response 스키마 | §9 Pydantic 스키마 | `app/schemas.py` |
| 근거 불충분 거절(환각 방지) | §6 거절 3경로 | `app/rag.py` `answer()`, `finalize()` |
| 비밀값 환경 변수 | §10 `.env` + `.gitignore` | `.env.example`, `app/llm.py` |
| 스트리밍(가점) | §9.3 SSE `delta`, `final` 이벤트 | `app/api.py` `_sse()` |

## 2. Corpus: 법령 24건, 조문 894개, 판례 400건, 판례 347건이 조문 150개에 연결

- 법령: 8개 법률 × (법률, 시행령, 시행규칙) = 현행 24건 + 시행예정 버전 11건 (`data/manifest.json`, status 현행 24, 시행예정 11)
- 조문 노드 894개, 이 중 시행예정 버전에만 있는 조문 1개 (`data/processed/provision_graph.json`)
- 판례: 코퍼스 8개 법률 관련 2010년 이후 대법원 판례 400건, 판시사항 + 판결요지 (`data/raw/precedents/`, `data/index/precedent/meta.json` precedents 400)
- 판례 → 조문 연결: 판례 347건이 조문 150개에 참조조문으로 연결 (`provision_graph.json`의 `precedents` 필드 집계)
- 출처: 국가법령정보 공동활용 OPEN API(`target=eflaw`, `prec`), 원문 XML 스냅샷 저장소 포함 - 법령, 판결은 저작권법 제7조 비보호 저작물
- 선정 근거: 최근 개정으로 모델 사전 지식과 현행 조문이 어긋남 → 문맥 없는 질의 시 오래된 사실 정답 100%, 최근 개정 사실 정답 40%(수기 재판정) (`docs/findings/2026-10-01-closed-book.md`, `eval/results/closed_book_v0_summary.json`)

## 3. 인제스트: 파싱 → Provision Graph → 색인, LLM 호출 0회

### 3.1 파싱 (`app/ingest/parse.py`)
- 법령 XML을 규칙으로 조, 항, 호 구조로 파싱, 조마다 `[법령명 > 장 > 조]` 헤더 부착
- 조문 ID 형식 `법령명#조`(예: `근로기준법#60`) - 인용, 검색 결과, GT 정답 근거가 같은 ID를 공유해 검색 적중을 기계적으로 대조

### 3.2 Provision Graph (`app/ingest/provision.py`, `app/ingest/precedent.py`)

| 연결 | 산출 방식 | 규모 |
|---|---|---|
| 시행 예정 개정 | 현행 ↔ 시행예정 버전 조문 대조, 공식 시행일 부여 | 조문 29개 |
| 부칙 유효기간(효력 상실) | 부칙 "…까지 효력을 가진다" 파싱, 이후 재개정된 항은 제외 | 조문 2개 |
| 위임 | 시행령, 시행규칙의 "법 제N조", "영 제N조" 인용 | 상위 조문을 가진 조문 336개 |
| 같은 법 안 참조 | "제N조" 열거 + 문장 단서 분류 | 간선 701개(예외 57, 준용 48, 일반 596) |
| 판례 → 조문 | 판례 참조조문 파싱, "구 법(전부개정 전)"은 연결 제외 | 판례 347건 → 조문 150개 |

- 출처: `data/processed/provision_graph.json` 집계 (2026-10-03 재집계)
- 시행 상태 6종: 시행 중, 시행 중(개정 예정), 일부 효력 상실, 효력 상실, 아직 시행 전, 확인 필요 - 기준일(`as_of`)을 받아 `status_at()`이 결정적으로 계산

### 3.3 Embedding, Index (`app/index.py`)
- 임베딩: 로컬 `nlpai-lab/KURE-v1`(bge-m3 기반 한국어 검색 파인튜닝, 입력 8,192토큰), revision `8b418a58` 고정
- 선택 근거: 엘리스 ML API 카탈로그에 임베딩 모델 부재 → 로컬 실행, 크레딧 0원
- 색인: FAISS `IndexFlatIP`(정규화 벡터 내적 = 코사인), 정확 검색 → 동일 질의 동일 결과, 평가에서 검색 단계 노이즈 0 (`eval/results/noise_floor.json` Measure 1 range 0)
- 색인 4종: 조 전체 894벡터(기본), 항, 호 분할 971벡터(비교용), 고정 길이 415벡터(비교용), 판례 400벡터(연결 판례 정렬 전용, 독립 검색 대상 아님) (`data/index/{whole,article,fixed,precedent}/meta.json`)
- 저장소: 서버형 Vector DB 미사용 - 수 MB 규모, 읽기 전용, 파일만으로 재현 가능, 법령 수천 건, 다중 서버, 수시 개정 시 pgvector/Qdrant 전환 조건

## 4. Chunking: 조 전체 색인 채택 - 검색 지표 동일, 분할 조문 질문 개선, 고정 길이는 인용 정밀도 0.306으로 기각

### 4.1 세 방식
| 방식 | 단위 | 벡터 수 | 용도 |
|---|---|---|---|
| **whole(기본)** | 조 1개 = 벡터 1개, 최장 조 약 2.5k토큰 < 모델 한도 8,192 | 894 | 기본 구성 |
| article | 조 단위, 512토큰 초과 조만 항(필요 시 호) 경계에서 분할, 헤더 반복 | 971 | 2차 실험 기준선 |
| fixed | 법령 전체를 512토큰 창, 64토큰 겹침으로 절단, 조 경계 무시 | 415 | 비교 실험 |

### 4.2 측정 비교

검색 지표 (LLM 호출 없음, `make retrieval ARGS="--strategy <s>"`, GT v2.2 정답 근거 보유 92문항, 2026-10-03 재실행)

| 방식 | Recall@5(any) | Recall@5(all) | MRR |
|---|---|---|---|
| whole | 0.924 | 0.696 | 0.801 |
| article | 0.924 | 0.696 | 0.799 |
| fixed | 0.935 | 0.696 | 0.808 |

답변 지표 (기준선 = article 3회 평균, `eval/results/v2/v2-h1-fixed/diff_vs_base.json`, `eval/results/v2/v2-final/diff_vs_base.json`)

| 지표 | article(기준선) | fixed | whole + 판례(최종) |
|---|---|---|---|
| 과잉 거절 | 0.105 | **0.163(유의 악화)** | **0.065(유의 개선)** |
| 인용 정밀도 | 0.700 | **0.306(유의 악화)** | 0.573(유의 악화, 판례 인용 영향) |
| 완전 정답 | 0.692 | 0.620 | 0.772 |
| 분할 조문형 완전 정답(12문항) | 0.722 | 0.750 | 0.917 |

- fixed 기각 근거: 청크 하나가 여러 조문에 걸침 → 블록 인용이 무관 조문까지 포함, 조문별 시행 상태 부착 불가, 과잉 거절 증가
- fixed의 Recall(any) 0.935는 관대한 판정: 청크가 여러 조문에 걸치면 "걸치면 적중"
- whole 채택 근거
  - 검색 지표가 article과 사실상 동일(MRR 0.801 vs 0.799)
  - 인용, GT 판정 단위가 조 → 블록과 인용 단위 일치
  - 단서, 항 간 참조로 조를 쪼개면 의미 손실, 분할된 조의 나머지 조각이 문맥에서 빠지는 문제(g021 유형) 원천 차단 - 형제 청크 동반 실험이 노린 문제를 색인 단계에서 해소
- whole 단독 효과의 한계: 최종 구성은 whole과 판례 연결을 함께 바꾼 결과 → whole 단독의 답변 지표 유의 판정 없음(판례 연결 단독 대비 완전 정답 0.761 → 0.772, 각 1회 실행, `eval/results/v2/v2-precedents/diff_vs_base.json`과 `v2-final/diff_vs_base.json`의 exp 값)
- 대가: 긴 조는 벡터가 여러 주제의 평균 → 일부 문항 순위 하락(README 기록: g016, g030 1위 → 3위), 입력 토큰 증가(판례 포함 조건 5,581 → 6,075)
- 수치 정정: README의 "Recall all 0.739"는 2026-10-03 재실행에서 재현되지 않음(whole, article 모두 0.696), "두 방식 동일" 결론은 유지

## 5. 검색과 그래프 확장: 상위 5개 + 위임 최대 3 + 판례 최대 2, 질의당 평균 8.4블록

### 5.1 단계와 상한 (`app/rag.py` `build_blocks()`)

| 순서 | 단계 | 대상 | 상한, 임계값 | 기본 |
|---|---|---|---|---|
| ① | 조문 검색 | 질의 임베딩 → 조 전체 색인 코사인 | top-k 5 (API에서 1~20) | 켜짐 |
| ② | 형제 청크 | 분할된 조의 나머지 조각 | 최대 4 | 켜짐, whole에서는 분할 조문이 없어 무동작 |
| ③ | 위임 확장 | 상위 3개 검색 조문의 상위법, 시행령 | 최대 3블록 | 켜짐 |
| ④ | 역참조 확장 | 상위 3개 조문을 예외, 준용 단서로 참조하는 조문 | 최대 2블록 | 꺼짐(2차 실험에서 효과 미확인) |
| ⑤ | 시행 상태 산출 | 블록마다 기준일 기준 상태, 메모 | - | 켜짐 |
| ⑥ | 판례 연결 | 검색 조문(확장 블록 제외)에 연결된 판례 → 질의와 판례 임베딩 코사인 정렬 | `PREC_TAU` 0.54 이상 상위 2건, 판결요지 3,000자 초과 시 문장 경계 절단 | 켜짐 |

- 실측 블록 구성(최종 구성 100문항): 검색 500, 위임 223, 판례 117, 질의당 평균 8.4블록, 판례가 붙은 질의 67/100 (`runs/20261003-021055_final-noise-2/predictions.jsonl`, 로컬 실행 폴더)
- 판례는 독립 검색 대상이 아님 → 조문 근거 없이 판례만으로 답하는 경로 차단, 대신 판례가 연결된 조문을 검색이 놓치면 판례 도달 불가(l5b03, l5b08)

### 5.2 임계값 선정: 판례 임계값은 dev 분할만으로 결정

| 임계값 | 값 | 선정 방식 | 검증 상태 |
|---|---|---|---|
| `PREC_TAU` | 0.54 | dev 44문항 중 정답 판례가 후보에 있는 Case6 3건(l5b06 0.545, l5b09 0.613, l5b07 0.707, 모두 후보 1위)을 모두 남기는 최댓값 | 2026-10-03 재계산으로 세 값 재현 |
| `MAX_PRECEDENTS` | 2 | 입력 토큰 상한 목적의 설계값 | 실험 없음 |
| τ(거절 게이트) | 0.50 | 코드 주석상 dev 보정값, 보정 곡선 산출물은 저장소에 없음 | 미검증 - 재보정을 향후 과제로 분류 |
| 하이브리드 검색 가중치 | N 50, RRF K 60, BM25 가중 0.5 | dev 검색 지표(LLM 없음) 격자 탐색 8점 | 미채택(Part C) |

- test 문항(l5b02, l5b04, l5b05)의 판례 점수는 임계값 결정에 미사용
- 출처: `app/rag.py` 상수, `eval/retrieval_check.py`(`--grid`), `docs/plans/2026-10-03-overfit-vs-generalize-preregistration.md`

## 6. 거절: 3경로, 최종 구성 100문항 중 거절 14건(게이트 2, 모델 11, 인용 무효 1)

| 경로 | 조건 | LLM 호출 | `refusal_reason` |
|---|---|---|---|
| 검색 게이트 | 검색 1위 점수 < τ 0.50 | 없음 | `retrieval_below_tau` |
| 모델 거절 | 답변 첫 줄 `[정보 부족]` (프롬프트 규칙 7) | 1회 | `model_declined` |
| 인용 검증 실패 | 답변에 유효한 `[S#]` 인용 0건 | 1회 | `no_valid_citation` |

- 실측: 게이트 2건(l5b02, n30), 모델 거절 11건, 인용 무효 1건 (`runs/20261003-011009_v2-final-whole-precedents/predictions.jsonl`, 게이트 문항은 `eval/results/v2/v2-final/scores.jsonl`의 `refusal_reason`)
- 효과: 범위 밖 8문항 거절률 3회 평균 0.875(1.00, 0.75, 0.875), 과잉 거절 0.065 (`eval/results/noise_floor_final.json`)
- 한계: 범위 밖 거절 실패 문항(g039, g041)은 "근거 없음"을 밝히고 부가 설명을 붙이거나 틀린 전제를 바로잡은 답변 → 지표상 실패이나 환각 답변은 아님(Part B §8)
- 한계: 게이트가 l5b02를 막음 - 정답 판례는 연결되나 조문 검색 1위 점수 0.495 < 0.50 (2026-10-03 재계산)

## 7. 시행 상태 주입: 날짜 계산을 LLM에 맡기지 않음, 끄면 시점형 완전 정답 0.667 → 0.240

- 블록마다 `시행 상태(기준일 YYYY-MM-DD): …` 헤더 + 메모(예: "2026-12-08 시행 예정 modified (공포 …)") + 시행 예정 개정 항의 새 문언 주입 (`app/rag.py` `_render()`)
- 근거: 공식 현행본에도 효력을 잃은 조항(근로기준법 제16조, 제53조③⑥)과 시행 전 개정이 본문에 그대로 게재 (`docs/gt-feasibility.md`)
- 효과(시행 상태 표시 끄기 실험, 기준선 3회 평균 대비): 시점형 25문항 완전 정답 0.667 → 0.240(CI [−0.60, −0.24]), 전체 완전 정답 −0.127, 과잉 거절 +0.047, 모두 유의 악화 (`eval/results/v2/v2-h4-no-inject/diff_vs_base.json`)
- 응답의 인용마다 `status`, `status_notes` 동봉 → 사용자 화면에서도 시행 전, 효력 상실 구분 가능

## 8. 프롬프트와 인용 검증: 조문 → 대법원 판단 → 사안별 단서, 인용 없는 답변은 거절 처리

### 8.1 생성 프롬프트 `gen-v3-precedent` 규칙 요지 (`app/rag.py` `SYSTEM_PRECEDENT`)
- 근거 블록 밖 내용, 블록에 없는 판례, 행정해석 보충 금지
- 사실 문장마다 `[S#]` 인용
- 시행 상태에 효력 상실, 시행 예정이 있으면 사실과 날짜 명시, 기준일 주입
- 조문 내용 먼저 → 관련 판례가 있으면 "대법원은 …라고 판단했습니다(대법원 YYYY. M. D. 선고 사건번호 판결) [S#]" → "다만 판례는 개별 사안의 사실관계에 따라 달리 판단될 수 있습니다" 단서
- 판례 판단을 조문 내용처럼 서술 금지, 무관한 판례 블록 사용 금지
- 답할 수 없으면 첫 줄 `[정보 부족]` + 무엇이 없는지 한 문장
- 생성 설정: GPT-5.6 Luna, temperature 0, seed 42, reasoning none, 출력 상한 800토큰 (`app/llm.py`, `app/rag.py`)

### 8.2 인용 검증 (`app/rag.py` `finalize()`)
- 답변을 문장 단위로 나눠 `[S#]` 표기 수집 → 존재하지 않는 블록 번호는 버림
- 인용마다 블록 원문에서 해당 문장들과 문자 2-gram 겹침이 가장 큰 항을 `quote`(최대 300자)로 추출 → 답변 문장과 근거 문장의 대응 제시
- 조문 인용: 법령명, 조 표기, 국가법령정보센터 조문 URL, 시행 상태, 판례 인용: "대법원 YYYY. M. D. 선고 사건번호 판결", 판례 URL, `not_applicable`
- 유효 인용 0건 → `insufficient_context`(`no_valid_citation`)로 전환, 인용 없는 답변은 사용자에게 노출하지 않음
- 한계: 인용 검증은 블록 존재 여부만 확인, 인용 문장의 내용 일치는 평가 단계(Measure 5 Judge)에서만 측정

## 9. API: `POST /v1/query`, JSON 또는 SSE 스트리밍

### 9.1 엔드포인트 (`app/api.py`)
| 메서드, 경로 | 용도 |
|---|---|
| `POST /v1/query` | 질의 → 답변, 인용, 검색 결과, 메타 (JSON, `stream: true`면 SSE) |
| `GET /healthz` | 상태, 색인 전략, 서버 누적 비용 |

- 서버 기동 시 임베딩 모델, 색인 사전 적재(첫 요청 지연 제거), 서버 비용 상한 `SERVER_BUDGET_KRW`(기본 3,000원) 초과 시 LLM 호출 차단

### 9.2 Request / Response 스키마 (`app/schemas.py`)

| 요청 필드 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `question` | str, 1~500자 | - | 질문 |
| `top_k` | int, 1~20 | 10 | 조문 검색 개수 (2026-10-04 이전 5) |
| `as_of` | date | 요청일 | 시행 상태 판단 기준일 |
| `stream` | bool | false | SSE 스트리밍 |
| `precedents` | bool | true | 연결 판례 사용 |

| 응답 필드 | 내용 |
|---|---|
| `status` | `answered`, `insufficient_context` |
| `answer` | 본문, 근거마다 `[S#]`, 거절 시 null |
| `citations[]` | `source`, `source_type`(statute, precedent), `chunk_id`, `article_ids`, `law`, `article`, `quote`, `url`, `status`, `status_notes` |
| `retrieval[]` | `rank`, `chunk_id`, `article_ids`, `score`, `linked`, `via`(search, sibling, link, reverse, precedent) - GT 정답 근거와 같은 ID 형식 |
| `meta` | `model`, `prompt_version`, `strategy`, `as_of`, `latency_ms`, `usage`(input, output, cached_input), `cost_krw`, `refusal_reason` |

### 9.3 SSE 스트리밍 (`app/api.py` `_sse()`)
- `event: delta` 반복(본문 조각) → 마지막 `event: final` 1회(비스트리밍 응답과 같은 `QueryResponse` 전체)
- 게이트 거절은 `delta` 없이 `final`만 전송
- 인용은 `[S#]` 표기에서 사후 추출 → 스트리밍, 비스트리밍이 같은 인용 형식 공유

## 10. 비밀값: 키는 환경 변수만, `.env`는 Git 제외

- 환경 변수: `ELICE_API_KEY`, `ELICE_BASE_URL`, `LLM_MODEL`, `LAW_OC`(수집 시에만), 템플릿 `.env.example`(값 비어 있음)
- `.gitignore` 첫 줄 `.env`, 코드는 `python-dotenv` + `os.environ`으로만 읽음 (`app/llm.py`)
- CI 설계에서도 `ELICE_API_KEY`는 CI secret으로 주입(Part B §10)

## 11. 비용, 지연: 생성 1회 약 1.4~1.6원, p50 약 3.0초, 100문항 평가 1회 약 430원

| 항목 | 기준선(article, 판례 없음) | 최종 구성 | 출처 |
|---|---|---|---|
| 생성 호출당 평균 입력 토큰 | 3,576 | 6,075 | `runs/20261002-233903_baseline-v2`, `runs/20261003-011009_v2-final-whole-precedents`의 `predictions.jsonl`(로컬) |
| 생성 1회 평균 비용(캐시 미사용 실행) | 1.008원 | 1.357, 1.634원 | `eval/results/v2/{noise-v2-2,final-noise-2,final-noise-3}/scores.jsonl` |
| 생성 지연 p50, p90(캐시 미사용, 동시 4) | 2,825, 4,468ms | 2,929~3,038, 4,671~5,024ms | 같은 파일 `latency_ms` |
| 평가 1회(생성 + Judge, 캐시 미사용) | 282.53원 | 427.31, 440.01원 | `eval/results/v2/*/manifest.json` |

- 단가: 입력 304원, 캐시 입력 30원, 출력 1,827원 / 1M 토큰 (`app/llm.py` `PRICES`)
- 같은 구성도 실행마다 입력 토큰 집계가 다름(최종 구성 5,369~6,075) - 게이트웨이 프롬프트 캐시 처리 차이로 추정, 비교는 같은 조건 실행끼리
- 전체 사용량: `runs/` 실행 manifest 합계 5,342.8원(실행 290개, 로컬) - README의 "약 6,000원"은 manifest 밖 호출(프롬프트 dev 반복 등) 포함 추정치

## 12. 설계 결정과 트레이드오프

| 결정 | 채택 이유 | 대가 |
|---|---|---|
| 조 전체 색인 | 인용, 판정 단위 일치, 분할 조문 누락 차단 | 긴 조 순위 하락, 입력 토큰 증가 |
| 그래프 확장(검색 후 1단계) | 검색이 놓친 시행령, 상위법 확보(g042: 시행령 제43조를 법 제74조 연결로 확보) | 같은 법 안 참조만 연결, 다른 법 예외(n05), 일부 위임(n29) 미연결 |
| 판례는 연결로만 도달 | 조문 근거 없는 판례 답변 차단 | 조문 검색 실패 시 판례 도달 불가 |
| 시행 상태 결정적 산출 | LLM 날짜 계산 오류 제거, 시점형 품질 유지 | 시행 예정 개정 문언은 검색 색인에 없음(g031 "시간 단위 분할" 질의 검색 실패) |
| 검색 점수 게이트 | LLM 호출 없는 저비용 거절 | 기계적 거절(l5b02), τ 재보정 필요 |
| 단일 LLM(Luna) | 크레딧 5만원 안에서 반복 측정 횟수 확보 | 생성, 채점 동일 모델의 관대 편향(Part B §5) |
| 프레임워크 미사용 | 단계별 on/off 실험 플래그, 동작 설명 가능 | 직접 구현 범위 증가 |
| `IndexFlatIP` 정확 검색 | 결정적 결과 → 검색 노이즈 0 | 대규모 확장 시 근사 색인 필요 |

## 13. 알려진 한계

- 검색: Recall@5(all) 0.696 - 넓은 요약형, 사례형 질문에서 정답 조문이 6~16위로 밀림, 검색 개수 10은 0.815로 유의 개선(Part C)
- 요약형 8문항 완전 정답 0.500, 판례형 9문항 0.444 (`eval/results/v2/v2-final/report.json` by_level)
- 판례 불필요 질문에도 판례 부착(100문항 중 67문항) → 인용 정밀도 하락, 입력 토큰 증가
- 판례 선택: 판결 선후, 전원합의체 변경 관계 미반영(l5b01)
- 그래프: 다른 법을 가리키는 예외, 일부 위임 미연결
- 운영: 엘리스 게이트웨이 비스트리밍 출력 2,000토큰 상한(Judge 재시도 상한으로 반영, `eval/judge.py`)
- τ 0.50 보정 근거 산출물 부재
