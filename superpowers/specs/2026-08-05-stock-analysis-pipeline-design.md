# 주식 분석 → HTML → GitHub Pages → 카카오톡 링크 발송 파이프라인

## 목적

사용자가 대화 중 자연어로 종목을 지정하면, `us-stock-analysis:technical-analysis` 스킬로 분석하고,
그 결과를 고정된 플랫/미니멀 HTML 템플릿에 채워 리포트를 생성하고, GitHub에 push하여
GitHub Pages로 공개한 뒤, 그 링크를 카카오톡으로 발송하는 반복 가능한 파이프라인.

## 트리거

- 완전 수동. 스케줄링/자동 감시 없음.
- 사용자가 "애플 주가 분석해서 보내줘" 같은 자연어 요청을 할 때마다 아래 단계를 1회 실행.

## 파이프라인 단계

1. **종목 식별** — 회사명이 주어지면 티커 심볼로 매핑.
2. **분석 실행** — `us-stock-analysis:technical-analysis` 스킬을 사용해 최신 시세를 확인하고
   MA/RSI/MACD/볼린저/MTF/시그널 박스 등 표준 출력을 생성.
3. **투자날씨 점수(0~100) 산정** — 아래 공식으로 스킬 원점수와는 별도로 재산정.
4. **HTML 리포트 생성** — 고정 템플릿(`templates/report-template.html`)에 값 채워넣기.
5. **저장 및 배포** — `docs/reports/<TICKER>-<YYYYMMDD>.html` 에 저장 →
   `git add` / `commit` / `push` to `main`.
6. **링크 생성** — `https://21dec.github.io/ai-stock-analysis/reports/<TICKER>-<YYYYMMDD>.html`
7. **카카오톡 발송** — PlayMCP `KakaotalkChat_MemoChat` 도구로 요약 메시지 발송.

각 실행마다 4~7단계(HTML 생성, git push, 카카오톡 발송)를 자동으로 수행하는 것이
이 파이프라인의 목적이므로, 매 실행 시 별도 승인 절차 없이 진행한다. 다만 실행 시작 시
"OOO 분석 후 push하고 카카오톡으로 보내겠습니다" 형태로 무엇을 할지 먼저 알린다.

## 사전 준비 (1회성, 이번 세션에서는 완료 불가)

- **GitHub Pages 활성화**: 저장소(`21dec/ai-stock-analysis`)가 public이라는 전제 하에,
  `main` 브랜치의 `/docs` 폴더를 Pages 소스로 설정. `gh` CLI가 이번 환경에서는
  `github.daumkakao.com`에만 로그인되어 있어 github.com API를 직접 호출할 수 없으므로,
  사용자가 GitHub 웹 UI(Settings → Pages → Source: `main` / `docs`)에서 최초 1회 설정해야 한다.
- **카카오톡 발송 도구 연결**: `KAKAOTALK_DELIVERY_POLICY.md`가 가리키는 PlayMCP
  `KakaotalkChat_MemoChat` 도구는 현재 세션에 연결되어 있지 않다(현재는 카카오워크 MCP만 연결).
  파이프라인 실행 시 이 도구가 없으면, HTML 생성/push는 완료하고 카카오톡 발송 단계에서
  "도구 미연결"로 명확히 실패를 보고한다. 자동으로 다른 채널로 대체하거나 조용히 생략하지 않는다.

## 투자날씨 점수 (0~100) 산정 공식

technical-analysis 스킬이 자체적으로 내는 `Score X.X/10`을 그대로 10배 하지 않고,
아래 네 요소를 조합해 별도로 산정한다.

| 요소 | 가중치 | 산정 방식 |
|---|---|---|
| Signal Score (스킬의 X.X/10) | 50% | 값 × 10 |
| Confidence | 20% | HIGH=100, MEDIUM=60, LOW=30 |
| MTF Alignment (X/3) | 20% | 값 ÷ 3 × 100 |
| RSI 과열/침체 보정 | 10% | RSI>70 또는 RSI<30이면 감쇄(50점), 40~60 중립 구간이면 가산(100점), 그 외 70점 |

최종 점수 = 각 요소 값 × 가중치의 합산 (0~100 범위로 clamp).

날씨 아이콘 매핑:

| 점수 구간 | 아이콘 | 라벨 |
|---|---|---|
| 80~100 | ☀️ | 맑음 (강한 매수) |
| 60~79 | 🌤️ | 대체로 맑음 (매수 우위) |
| 40~59 | ⛅ | 흐림 (중립) |
| 20~39 | 🌧️ | 비 (매도 우위) |
| 0~19 | ⛈️ | 폭풍 (강한 매도) |

## HTML 리포트 템플릿 (플랫/미니멀, 고정)

디자인은 부차적 요소이므로 화려함보다 고정성과 단순함을 우선한다.

- 그라디언트·히어로 배너·큰 그림자 없음. 상단은 얇은 타이틀 바(종목명 + 티커 + 날짜)만.
- 배경은 흰색/오프화이트 단색, 텍스트는 짙은 회색/블랙, 포인트 컬러 1개(파란색 계열)만 사용.
- 카드/테이블은 1px 균일 보더 + 옅은 배경, 그림자 없음.
  - **사용자 CLAUDE.md 규칙 준수**: 좌측 보더 강조(`border-left`, 세로줄 콜아웃)는 절대 사용하지
    않는다. 강조가 필요하면 4방향 균일 보더 또는 배경색으로 대체.
- 투자날씨는 아이콘 + 점수 + 라벨의 작은 배지(pill) 형태로 표시.
- 시그널 박스(BULLISH/NEUTRAL/BEARISH)는 워터마크 없이 텍스트 + 색상 배지로 단순화.
- 이 템플릿을 `templates/report-template.html`로 고정하고, 매 실행 시 값만 채워 재사용한다
  (report-generator 스킬의 화려한 기본 템플릿은 사용하지 않음).

## 카카오톡 메시지 포맷

기존 `KAKAOTALK_DELIVERY_POLICY.md`가 규정한 "분석 전문 전체를 한 메시지로 전송" 방식은
이 파이프라인에서는 적용하지 않는다. 요약 + 링크로 대체하고, 정책 문서도 이 변경을 반영해
갱신한다.

```
[종목명(티커)] 투자 분석
현재가: $[PRICE]
투자날씨: ☀️ 82점 (맑음)
📄 상세 리포트: https://21dec.github.io/ai-stock-analysis/reports/AAPL-20260805.html
```

## 파일/경로 구조

```
templates/report-template.html   # 고정 HTML 템플릿
docs/reports/<TICKER>-<YYYYMMDD>.html   # 생성된 리포트 (GitHub Pages 소스 폴더)
KAKAOTALK_DELIVERY_POLICY.md     # 갱신 대상 (요약+링크 방식 반영)
```

## 에러 처리

- 카카오톡 발송 도구가 연결되어 있지 않으면: HTML 생성/push는 완료된 상태로 두고,
  발송 실패와 그 원인을 사용자에게 명확히 보고한다. 자동 재시도나 대체 채널 사용 없음.
- git push 실패(충돌 등) 시: 자동으로 강제 push하지 않고 원인을 보고한다.
- 실시간 시세를 가져올 수 없으면: technical-analysis 스킬의 데이터 검증 규칙(라이브 데이터
  없을 시 경고 표시)을 그대로 따른다.
