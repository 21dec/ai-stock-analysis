# 주식 분석 파이프라인 실행 방법 (Claude용 운영 가이드)

사용자가 "OOO 분석해서 보내줘" 라고 요청하면 아래 순서를 그대로 따른다.
설계 배경은 `superpowers/specs/2026-08-05-stock-analysis-pipeline-design.md` 참고.

## 사전 조건 (1회성 — 아직 완료되지 않았다면 사용자에게 안내)

1. **GitHub Pages**: `21dec/ai-stock-analysis` 저장소가 public이고, `main` 브랜치의
   `/docs` 폴더가 Pages 소스로 설정되어 있어야 한다. 안 되어 있으면 사용자에게
   GitHub 웹 UI(Settings → Pages → Source: `main` / `docs`)에서 설정을 요청한다.
2. **카카오톡 발송 도구**: PlayMCP `KakaotalkChat_MemoChat` (또는 동등한) MCP 도구가
   세션에 연결되어 있어야 한다. 연결되어 있지 않으면 4~5단계(HTML 생성, git push)는
   진행하고, 6단계(카카오톡 발송)에서 도구 미연결을 사용자에게 명확히 보고한다.

## 실행 순서

1. **종목 식별** — 회사명이 주어지면 티커 심볼로 매핑한다 (예: "애플" → `AAPL`).
2. **분석 실행** — `us-stock-analysis:technical-analysis` 스킬을 실행해 최신 시세와
   표준 출력(MA, RSI, MACD, 볼린저, MTF 정렬 점수, 시그널 박스, Thesis Invalidation)을
   얻는다. 스킬의 데이터 검증 규칙(라이브 데이터 없으면 경고 표시)을 그대로 따른다.
3. **입력 JSON 작성** — 스킬 출력에서 다음 값을 추출해 임시 JSON 파일로 만든다
   (예: `/tmp/report-input.json`):

   ```json
   {
     "ticker": "AAPL",
     "company": "Apple Inc.",
     "date": "20260805",
     "price": "$185.32",
     "signal_score_10": 8.4,
     "confidence": "HIGH",
     "mtf_alignment_3": 3,
     "rsi": 55.0,
     "signal": "BULLISH",
     "horizon": "LONG-TERM",
     "analysis_body_html": "<h2>추세</h2><p>...</p><h2>지지/저항</h2><table>...</table>..."
   }
   ```

   - `signal_score_10`: 스킬이 출력하는 `Score: X.X / 10` 값.
   - `confidence`: 스킬이 출력하는 `Confidence: HIGH/MEDIUM/LOW`.
   - `mtf_alignment_3`: MTF 정렬 점수 `X/3`의 `X`.
   - `rsi`: 가장 최근(주로 primary timeframe) RSI(14) 값.
   - `signal`: `BULLISH`/`NEUTRAL`/`BEARISH`.
   - `analysis_body_html`: 스킬이 만든 분석 본문(추세, 지지/저항, 지표, 패턴, Thesis
     Invalidation 등)을 `<h2>`/`<table>`/`<ul>` 등 기본 HTML 태그로 직접 작성한다.
     별도 변환 스크립트는 없다 — Claude가 이 HTML을 직접 작성한다.

4. **HTML 생성** — 다음 명령으로 리포트를 만든다:

   ```bash
   PYTHONPATH=. python3 scripts/generate_report.py /tmp/report-input.json
   ```

   표준출력으로 `{"report_path": "...", "pages_url": "...", "kakao_message": "..."}`
   JSON이 출력된다. 이 세 값을 이후 단계에서 사용한다.

5. **git push** — 생성된 `report_path` 파일을 커밋하고 push한다:

   ```bash
   git add docs/reports/<TICKER>-<YYYYMMDD>.html
   git commit -m "Add <TICKER> analysis report for <YYYYMMDD>"
   git push origin main
   ```

   push가 실패하면(충돌 등) 강제 push하지 않고 원인을 사용자에게 보고한다.

6. **카카오톡 발송** — 4단계에서 얻은 `kakao_message`를 PlayMCP
   `KakaotalkChat_MemoChat` 도구로 그대로 전송한다. 메시지를 축약·분할하지 않는다.
   도구가 연결되어 있지 않으면 발송 실패를 명확히 보고하고, HTML 생성/push는
   완료된 상태임을 알린다.

## 참고

- 투자날씨 점수 공식은 `scripts/pipeline/weather_score.py`에 고정되어 있다.
  공식을 바꾸려면 스펙 문서와 이 스크립트를 함께 갱신한다.
- HTML 템플릿은 `templates/report-template.html`에 고정되어 있다. 매 실행마다
  값만 채워 넣고, 템플릿 구조 자체는 바꾸지 않는다.
