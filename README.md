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
