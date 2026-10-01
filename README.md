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
