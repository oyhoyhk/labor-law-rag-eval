# 노동법령 RAG QA + 자체 Eval Harness

노동 관계 법령 24건(법·시행령·시행규칙)을 근거로 답하는 Citation 기반 RAG 서비스와, 그 품질을 측정하는 자체 평가 체계

> 설계 문서: [docs/design.md](docs/design.md) · 실측 기록: [docs/findings/](docs/findings/)

## Corpus: 노동 관계 법령 24건

- 구성: 근로기준법·최저임금법·근로자퇴직급여 보장법·남녀고용평등법·기간제법·파견법·근로자참여법·임금채권보장법 × (법률·시행령·시행규칙), 조문 893개, 본문 약 255페이지
- 출처: 국가법령정보 공동활용 OPEN API(`target=eflaw`) 현행본 + 시행예정 버전 11개, 원문 XML 스냅샷을 저장소에 포함(공공저작물, 저작권법 제7조)
- 선정 이유
  - 정답이 수치·조건·예외로 결정되어 판정 가능: 조문 문장과 대조해 채점
  - 위임 구조(법 → 시행령 → 시행규칙)와 조문 간 참조로 다중 근거 추론 질의가 자연스럽게 발생
  - **최근 개정으로 모델 사전 지식과 현행 조문이 어긋남** → Hallucination 관측 가능. 문맥 없이 질의(closed-book) 시 오래된 사실 100%, 최근 개정 사실 40% 정답(`docs/findings/2026-10-01-closed-book.md`)
  - 공식 현행본에도 효력을 잃은 조항(근로기준법 제16조, 제53조③⑥)과 시행 전 개정이 섞여 있어, 시점 판단이 필요한 실제 난제 포함

## 시스템 아키텍처

```
[수집]  law.go.kr OPEN API ──► data/raw/laws/*.xml (현행 + 시행예정 버전)
   │
[인제스트]
   ├ parse     조·항·호 구조 레코드 (app/ingest/parse.py)
   ├ provision 시행 상태 그래프: 시행예정 버전 diff + 부칙 유효기간 + 위임 관계 (provision_graph.json)
   ├ chunk     조 단위(512토큰 초과 시 항·호 경계 분할) / 고정 길이(비교용)
   └ index     KURE-v1 임베딩 → FAISS IndexFlatIP + chunks.jsonl
   │
[질의]  POST /v1/query (FastAPI, JSON·SSE)
   검색 top-5 ─► 위임 조문 확장(최대 3) ─► 거절 게이트(top-1 < τ 0.50)
   ─► 시행 상태 헤더 주입 ─► GPT-5.6 Luna 생성([S#] 인용) ─► 인용 검증 ─► 응답(조문 링크·시행 상태)
   │
[평가]  make eval
   Gold Set ─► 질의 API 경로 그대로 실행 ─► 결정적 지표(M1~M3) + Luna Judge(M4~M6)
   ─► report.md · manifest.json (모델·seed·프롬프트·Corpus·GT 해시·비용)
```

## 실행 방법

### 1. 설치

```bash
uv sync
cp .env.example .env   # LAW_OC, ELICE_API_KEY, ELICE_BASE_URL 입력
```

### 2. Corpus 수집 (선택 — 스냅샷이 `data/raw/`에 포함됨)

```bash
uv run python scripts/fetch_laws.py          # 법령 현행 + 시행예정 버전
uv run python scripts/fetch_precedents.py search 해고예고 --since 20150101
uv run python scripts/fetch_precedents.py fetch <판례일련번호>
```

- `LAW_OC`: [국가법령정보 공동활용](https://open.law.go.kr) OPEN API 활용신청 후 발급

### 3. 인제스트 (Provision Graph + 인덱스)

```bash
uv run python -m app.ingest.provision            # 시행 상태 그래프
uv run python -m app.index build --strategy article
uv run python -m app.index build --strategy fixed  # H1 비교용
uv run pytest -q
```

### 4. 서버 실행

```bash
uv run uvicorn app.api:app --port 8000
curl localhost:8000/v1/query -H 'Content-Type: application/json' \
  -d '{"question": "연차휴가를 시간 단위로 쓸 수 있나요?", "as_of": "2026-10-01"}'
# 스트리밍: "stream": true → SSE `delta` 이벤트 후 `final` 이벤트(전체 응답)
```

### 5. 평가 실행

```bash
make eval NAME=baseline                          # Gold Set 56문항 → RAG → Judge → runs/<시각>_<이름>/report.md
make eval NAME=h4-off ARGS="--no-inject"         # 실험: 시행 상태 주입 끄기
make eval NAME=noise-2 ARGS="--no-cache"         # 노이즈 측정: 캐시 없이 재실행
make retrieval ARGS="--strategy fixed"           # 검색 지표만(LLM 호출 없음)
make compare ARGS="diff runs/<기준> runs/<실험>"  # 노이즈 폭·부트스트랩 CI로 개선 판정
make calibrate                                   # Judge vs 사람 판정 일치도(κ)
```

- 실행 폴더: `predictions.jsonl`(답변·인용·검색 결과), `judgments.jsonl`(Judge 판정), `scores.jsonl`(문항별 지표), `report.md`, `manifest.json`(git·모델·seed·프롬프트·Corpus·GT 해시·비용)
- 재현성: seed 42·temperature 0 고정, LLM 응답 캐시(`data/cache/llm`, 동일 요청 0원), 실행당 예산 상한(`--budget`)

## 평가 지표와 한계

| 지표 | 무엇을 | 방식 | 기준선 v1.1 | 한계·맹점 |
|---|---|---|---|---|
| M1 검색 Recall@5 · MRR | 정답 조문이 검색됐나 | 결정적 (조문 ID 대조) | 0.895 · 0.786 | 조 단위 판정이라 긴 조문의 일부 조각만 검색돼도 적중(g021); 보조 근거(벌칙·정의)까지 같은 무게 |
| M2 거절 | Corpus 밖 거절 · L5b 단정 회피 · 과잉 거절 | status + Judge(결론 단정) | 1.00 · 1.00 · 0.039 | 표본이 작음(4·6건); 검색 임계값 거절과 모델 거절을 구분하지 않음 |
| M3 인용 정밀도·재현율 | 정답 조문을 인용했나 | 결정적 | 0.716 · 0.874 | 정답 외 조문 인용을 오류로 셈 — 보조 설명 인용과 잘못된 인용을 구분 못 함 |
| M4 정답 포인트 | 필요한 사실을 말했나 | Luna Judge 이진 판정 | 0.904 (전부 맞힘 0.776) | 생성·채점 동일 모델의 관대 편향(사람 대비 관대 3·엄격 1건); GT 포인트 문구가 좁으면 정답도 감점(v1.1에서 2건 수정) |
| M5 근거 없는 주장 | 근거 블록에 없는 말을 했나 | Luna Judge 주장 분해 + 판정 | 0.029 | 메타 진술 오탐; **분해 단계에서 틀린 문장을 고쳐 적어 오류를 놓침**(l5a01, l5b05); 사람 기준 κ 0.54로 보조 지표 취급 |
| M6 시점 오류 | 시행 전·효력 상실 조문을 현행처럼 말했나 | Luna Judge | 0.00 (6건) | 검색에 실패한 L4 문항(g031)은 측정 대상에서 빠짐 |
| 비용 · 지연 | | 결정적 | 56~61문항 약 100원 | |

- 노이즈 바닥(같은 설정 3회): 검색 지표 변동 0, 정답 포인트 ±0.035, 근거 없는 주장 ±0.023 → 실험 비교는 이 폭과 문항 단위 부트스트랩 95% CI를 함께 넘어야 개선으로 판정 (`make compare`)

## CI 연동 설계 (Regression 방지)

| 단계 | 트리거 | 내용 | LLM 비용 |
|---|---|---|---|
| 빠른 검사 | 모든 PR | `pytest`, `verify_gold`, 검색 지표(`make retrieval`) — 기준선 대비 하락 시 실패 | 0원 |
| 전체 평가 | `eval` 라벨 PR · 야간 | `make eval` 61문항, LLM 응답 캐시로 변경분만 호출, 예산 상한 | 수 원~100원 |
| 퇴행 판정 | 전체 평가 후 | `make compare diff 기준선 PR실행` — 노이즈 폭과 95% CI를 모두 넘는 하락만 실패 | 0원 |
| 결과 공유 | PR 코멘트 | 지표 표와 악화 문항 목록, `report.md`를 아티팩트로 첨부 | — |

- 비밀값(`ELICE_API_KEY`)은 CI secret, 임베딩 모델은 revision 고정으로 캐시
- Gold Set이 바뀌면(`gold_sha256` 변경) 기준선을 새로 고정하고 이전 기준선과 직접 비교하지 않음
- Judge 프롬프트 변경도 기준선 재고정 사유(`judge_version`)

## Judge 신뢰성

| 지표 | Judge | 사람 확인 판정과 일치 | 채택 |
|---|---|---|---|
| M4 정답 포인트 | Luna(judge-v2) | 96% · κ 0.78 (46건, 포인트 98개) | 채택 |
| M5 근거 없는 주장 | Luna(judge-v2) | 98% · κ 0.54 (주장 237개), 정밀도 0.375 | 보류(judge-v3 예정) |
| M6 시점 오류 · L5b 결론 단정 | Luna(judge-v2) | 전부 일치 (6건 · 2건) | 채택(표본 적음) |

- 일관성: 같은 답변 3회 채점 시 정답 포인트 판정 98~99% 일치 (`docs/findings/2026-10-02-judge-consistency.md`)
- 교차 검증: Claude Opus 교차 Judge는 사람보다 엄격, Luna는 관대 → 생성·채점 동일 모델의 관대 편향 확인 (`docs/findings/2026-10-02-cross-judge-opus.md`)
- 사람 판정 절차: Claude가 조문·검색 결과를 대조해 근거를 붙여 채점 → 사람이 56건 전부 동의/이의 확인(블라인드 아님, 동조 편향 가능) (`docs/findings/2026-10-02-judge-calibration.md`)
- 알려진 맹점: 주장 분해 단계에서 틀린 문장을 고쳐 적어 오류를 놓침(l5a01, l5b05)

## 설계 결정

### 검색 저장소: FAISS 인덱스 + 메타데이터 파일 (서버형 Vector DB 미사용)
- 구성: `faiss.index`(벡터) + `chunks.jsonl`(순번 → 본문·조문 ID) + `provision_graph.json`(조문 연결·시행 상태)
- FAISS = 유사도 검색 인덱스 라이브러리. 원문·메타데이터·필터·CRUD는 직접 관리
- 선택 근거
  - 규모: 조문 894개 · 청크 972개 · 연결 336개 → 전량 메모리 적재 가능(수 MB)
  - 읽기 전용: 인제스트 시 1회 생성, 질의 중 변경 없음 → 트랜잭션·동시 쓰기 불필요
  - `IndexFlatIP` 정확 검색: 동일 질의 동일 결과 → 평가에서 검색 단계 노이즈 0
  - 재현성: 설치 없이 파일만으로 재현, Corpus 해시와 함께 버전 고정
- 전환 조건: 법령 수천 건 이상·다중 서버·수시 개정 반영 → pgvector/Qdrant(벡터), Postgres 테이블 또는 그래프 DB(조문 연결)

### 인덱스 단위: 조(條)
- 1 청크 = 1 조, 512토큰 초과 시 항·호 경계 분할(머리말 `[법령 > 장 > 조]` 반복)
- 근거: 단서·항 간 참조로 항 단독 분리 시 의미 손실, 인용·GT 판정 단위가 조
- 비교 실험: 고정 길이 512토큰 분할(H1)

### 시행 상태: 인제스트 단계에서 결정적 산출
- 공식 시행예정 버전과 현행 비교 + 부칙 유효기간 파싱 → 조문별 상태(시행 중·개정 예정·효력 상실)
- 질의 시 검색된 조문에 상태 헤더 주입, 날짜 계산을 LLM에 맡기지 않음
- 근거: 공식 현행본에도 효력 상실 조항(근로기준법 제16조, 제53조③⑥)이 그대로 게재됨

### 조문 연결: 검색 후 그래프 확장
- 시행령·시행규칙의 "법 제N조"·"영 제N조" 인용으로 위임 관계 연결, 검색 상위 3개 결과에서 1단계 확장(최대 3개)
- 효과 실측: g042(임신 10주 유산) — 검색 실패한 시행령 제43조를 법 제74조 연결로 확보
- 미구현: 같은 법 내 조문 참조, 타 법률 참조, 연결 조문의 관련도 정렬

### 임베딩: 로컬 nlpai-lab/KURE-v1
- 엘리스 ML API 카탈로그에 임베딩 모델 부재 → 로컬 실행, 크레딧 0원
- bge-m3 기반 한국어 검색 파인튜닝, MIT, revision 고정

### LLM: GPT-5.6 Luna 단일 모델 (답변 생성 + Judge)
- 비용: 입력 304원·출력 1,827원 / 1M 토큰, 크레딧 5만원 한도
- 한계: 생성·채점 동일 모델 → 자기 선호 편향 가능, 이진 체크리스트 채점과 사람 판정 일치도 측정으로 완화

### 프레임워크 미사용
- LangChain·LlamaIndex 없이 파싱·청킹·검색·주입·인용 검증 직접 구현
- 근거: 파이프라인 단계별 동작을 설명·측정 가능하게 유지

## Gold Set (`eval/gold/gold_v1_1.jsonl`, 61문항)

| 단계 | 문항 | 기대 응답 |
|---|---|---|
| L1 단일 조문 사실 | 10 | 답변 |
| L2 조건·단서·경계값 | 11 | 답변 |
| L3 다중 조문·위임·계산 | 10 | 답변 |
| L4 시점(시행예정·효력 상실) | 7 | 답변 + 시행일·효력 상태 명시 |
| Corpus 밖·잘못된 전제 | 4 | 근거 불충분 |
| L5a 판례 사례 — 조문으로 결론 도출 | 8 | 답변 |
| L5b 판례 사례 — 판례 해석 의존 | 6 | 조문 인용 + 단정 회피(거절 또는 부분 답변) |
| SUM 요약 | 5 | 여러 항·조문을 묶어 정리 |

구축 과정
1. AI 작성(Opus): 조문 원문 기준 문항·정답 포인트 작성, 대법원 판례 후보 20건 중 14건 선정
2. 기계 검증: 정답 포인트 문자열이 근거 조문에 실제로 있는지 검사 — `uv run python scripts/verify_gold.py`
3. 타 모델 독립 재검토(Fable): OK 35 / 경미 10 / 중대 11 → 중대 11건 수정 (`eval/gold/review_v1_independent.md`)
4. 사람 최종 검토: 국가법령정보센터 원문 캡처·판결요지·재검토 의견을 대조해 56건 전부 확인 (`eval/gold/human_review_v1.jsonl`)
5. v1.1: 요약형 5문항 추가, 시스템 답변 채점 확인 과정에서 드러난 GT 문구 문제 3건 수정 (`eval/gold/CHANGELOG.md`)

한계: 단일 작성 계열(AI)·단일 검토자, 쟁점이 명확한 판례 위주 선정, 법률 문어체 질의 비중이 높음
