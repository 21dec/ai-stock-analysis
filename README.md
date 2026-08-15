# my-stock

개인 주식투자를 위한 **근거 기반 의사결정 시스템**이다. 목표는 상승·하락을 단정하는 것이 아니라, 같은 입력과 정책에서 같은 분석 결과를 만들고 실제 판단의 결과를 사후 검증할 수 있게 하는 것이다.

## 제품 원칙

1. 모든 결론은 출처가 있는 원자 주장으로 추적한다.
2. 기술·펀더멘털·뉴스 분석을 독립적으로 수행한다.
3. 상승·기준·하락 시나리오에는 관찰 가능한 조건과 무효화 기준이 있어야 한다.
4. 반대 검토와 결정적 검증을 통과한 분석만 보고서로 만든다.
5. 분석과 주문 실행을 분리한다. 현재 시스템은 주문을 생성하거나 전송하지 않는다.
6. 실제 투자 판단과 결과를 기록해 분석 방법 자체를 평가한다.

## MVP 흐름

```text
시장 데이터·공시·뉴스
        ↓
독립 분석 그래프
        ↓
evidence.json
        ↓
결정적 검증 ── 실패 → 보고서 생성 중단
        ↓
HTML 시나리오 보고서
        ↓
사용자 판단 기록
        ↓
사후 성과 평가
```

현재 수직 기능은 `분석 그래프 → evidence 검증 → 로컬 이력 → GitHub Pages 공개`까지 연결돼 있다.

## 실행

### Evidence 보고서 생성

```bash
PYTHONPATH=. python3 scripts/generate_evidence_report.py \
  artifacts/runs/20260814-SKHYNIX-daily/evidence.json
```

검증에 실패하면 HTML 파일을 만들지 않고 오류 목록을 반환한다.

### PostgreSQL 분석 이력 인덱스

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

createdb -h localhost -p 5432 my_stock
.venv/bin/alembic upgrade head

PYTHONPATH=.:src .venv/bin/python scripts/index_artifacts.py
```

기본 연결 주소는 `postgresql+psycopg://localhost:5432/my_stock`이다. 다른 연결을 사용할 때는 비밀번호를 코드에 기록하지 않고 `MY_STOCK_DATABASE_URL` 환경변수로 전달한다.

PostgreSQL 통합 테스트는 별도의 `my_stock_test` 데이터베이스를 사용한다.

```bash
createdb -h localhost -p 5432 my_stock_test
MY_STOCK_TEST_DATABASE_URL=postgresql+psycopg://localhost:5432/my_stock_test \
  PYTHONPATH=.:src .venv/bin/python -m unittest discover -s tests -v
```

### 분석 이력 웹 제품

마이그레이션과 인덱싱을 마친 뒤 로컬 서버를 실행한다.

```bash
.venv/bin/python -m my_stock_web
```

브라우저에서 `http://127.0.0.1:7800`을 열면 홈 요약, 검색·필터, 종목별 분석 연대기를 볼 수 있다. 분석 상세에서는 전문 애널리스트 형식의 종합 의견, 관점별 판단, 판단을 바꿀 신호와 조건별 시나리오를 먼저 읽고, 원자 주장·출처·충돌·한계를 근거 부록에서 검토할 수 있다. 동일 종목의 두 실행 비교와 `/system` 운영 상태 화면도 제공한다. 서버는 시작 직후와 이후 60초마다 유효한 artifact를 PostgreSQL 파생 인덱스와 동기화하며 원본 파일을 수정하지 않는다.

동기화 간격은 `MY_STOCK_SYNC_INTERVAL_SECONDS`로 조정할 수 있으며 기본값은 60초다.

### 전체 자동 실행·게시

감시 종목과 공개 주소는 `config/stock-automation.json`에서 관리한다. 분석 완료 후 다음 명령 하나로 검증, HTML 생성, PostgreSQL 동기화, Pages 인덱스 갱신, 선택적 커밋·푸시·공개 확인을 수행한다.

```bash
PYTHONPATH=. .venv/bin/python scripts/publish_stock_pages.py \
  --sync-db --commit --push --verify
```

검증 실패, 감시 종목 누락, 동일 종목·기준일 중복, 관련 없는 staged 파일이 있으면 게시 전에 중단한다. 변경이 없으면 빈 커밋을 만들지 않는다. 평일 반복 분석은 `.agents/skills/run-and-publish-stock-analysis/`을 호출하는 Codex 자동화가 수행한다.

## 주요 디렉터리

```text
.agents/skills/run-stock-analysis-graph/  분석 그래프의 에이전트 인터페이스
.agents/skills/run-and-publish-stock-analysis/ 전체 실행·게시 자동화 인터페이스
config/stock-automation.json              감시 종목과 Pages 설정
scripts/pipeline/                         검증·렌더링 도메인 로직
scripts/generate_evidence_report.py       evidence 기반 보고서 CLI
scripts/index_artifacts.py                PostgreSQL 증분 인덱싱 CLI
scripts/publish_stock_pages.py            검증·DB·Pages·Git 자동 게시 CLI
src/my_stock_web/                         웹 제품의 DB·인덱서·서버·화면
migrations/                               Alembic schema migration
artifacts/runs/<run-id>/                  실행별 증거와 보고서
evals/cases/                              결정적 검증 fixture
tests/                                    단위·통합 테스트
docs/                                     GitHub Pages 인덱스와 공개 보고서
```

기존 `scripts/generate_report.py`와 `docs/reports/`는 실험 단계의 호환 경로다. 신규 기능은 검증된 evidence artifact와 `artifacts/runs/`를 기준으로 개발한다.

## 문서

- [제품 정의](docs/PRODUCT.md)
- [아키텍처](docs/ARCHITECTURE.md)
- [분석 이력 웹 제품 계획](docs/WEB_PRODUCT_PLAN.md)
- [웹 UI 디자인 계약](docs/UI_DESIGN_CONTRACT.md)
