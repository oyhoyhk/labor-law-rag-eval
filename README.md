# 노동법령 RAG QA + 자체 Eval Harness

노동 관계 법령 24건(법·시행령·시행규칙)을 근거로 답하는 Citation 기반 RAG 서비스와, 그 품질을 측정하는 자체 평가 체계

> 작업 중 — 설계: [docs/design.md](docs/design.md)

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

## Gold Set (`eval/gold/gold_v1.jsonl`, 56문항)

| 단계 | 문항 | 기대 응답 |
|---|---|---|
| L1 단일 조문 사실 | 10 | 답변 |
| L2 조건·단서·경계값 | 11 | 답변 |
| L3 다중 조문·위임·계산 | 10 | 답변 |
| L4 시점(시행예정·효력 상실) | 7 | 답변 + 시행일·효력 상태 명시 |
| Corpus 밖·잘못된 전제 | 4 | 근거 불충분 |
| L5a 판례 사례 — 조문으로 결론 도출 | 8 | 답변 |
| L5b 판례 사례 — 판례 해석 의존 | 6 | 근거 불충분(조문만으로 단정 불가) |

구축 과정
1. AI 작성(Opus): 조문 원문 기준 문항·정답 포인트 작성, 대법원 판례 후보 20건 중 14건 선정
2. 기계 검증: 정답 포인트 문자열이 근거 조문에 실제로 있는지 검사 — `uv run python scripts/verify_gold.py`
3. 타 모델 독립 재검토(Fable): OK 35 / 경미 10 / 중대 11 → 중대 11건 수정 (`eval/gold/review_v1_independent.md`)
4. 사람 최종 검토: 국가법령정보센터 원문 캡처·판결요지·재검토 의견을 대조해 56건 전부 확인 (`eval/gold/human_review_v1.jsonl`)

한계: 단일 작성 계열(AI)·단일 검토자, 쟁점이 명확한 판례 위주 선정, 법률 문어체 질의 비중이 높음
