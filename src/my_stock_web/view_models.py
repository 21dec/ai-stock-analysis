"""Presentation-only transformations for server-rendered views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from my_stock_web.models import AnalysisRun, IndexError, Source

SEOUL = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class AnalysisRow:
    run_id: str
    ticker: str
    display_name: str
    exchange: str
    exchange_label: str
    timeframe: str
    timeframe_label: str
    horizon: str
    horizon_label: str
    as_of_date: str
    as_of_time: str
    source_count: int
    claim_count: int
    review_verdict: str
    review_verdict_label: str
    report_available: bool


@dataclass(frozen=True)
class SourceView:
    source_id: str
    title: str
    url: str | None
    published_at: str
    retrieved_at: str
    source_type: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class ClaimView:
    claim_id: str
    lane: str
    kind: str
    kind_label: str
    text: str
    confidence: str
    sources: tuple[SourceView, ...]


@dataclass(frozen=True)
class LaneView:
    name: str
    label: str
    status: str
    status_label: str
    reason: str | None
    claims: tuple[ClaimView, ...]


@dataclass(frozen=True)
class ScenarioView:
    name: str
    label: str
    thesis: str
    triggers: tuple[str, ...]
    invalidation: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnalystKeyPointView:
    title: str
    assessment: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnalystPerspectiveView:
    name: str
    label: str
    impact: str
    impact_label: str
    conclusion: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnalystMonitoringView:
    signal: str
    interpretation: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnalystReportView:
    stance: str
    stance_label: str
    confidence: str
    confidence_label: str
    headline: str
    summary: str
    key_points: tuple[AnalystKeyPointView, ...]
    perspectives: tuple[AnalystPerspectiveView, ...]
    monitoring_points: tuple[AnalystMonitoringView, ...]
    final_assessment: str
    final_claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisDetail:
    run_id: str
    ticker: str
    display_name: str
    exchange: str
    exchange_label: str
    currency: str
    currency_label: str
    timeframe: str
    timeframe_label: str
    horizon: str
    horizon_label: str
    as_of_date: str
    as_of_time: str
    review_verdict: str
    review_verdict_label: str
    reviewed_at: str
    order_action: str
    source_count: int
    claim_count: int
    report_available: bool
    analyst_report: AnalystReportView | None
    scenarios: tuple[ScenarioView, ...]
    lanes: tuple[LaneView, ...]
    sources: tuple[SourceView, ...]
    conflicts: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ComparisonMetricView:
    label: str
    before: str
    after: str
    change: str


@dataclass(frozen=True)
class ScenarioComparisonView:
    name: str
    label: str
    before: str
    after: str
    changed: bool


@dataclass(frozen=True)
class ClaimChangeView:
    change_type: str
    change_label: str
    claim_id: str
    before: str | None
    after: str | None


@dataclass(frozen=True)
class AnalysisComparisonView:
    before: AnalysisDetail
    after: AnalysisDetail
    metrics: tuple[ComparisonMetricView, ...]
    scenarios: tuple[ScenarioComparisonView, ...]
    claim_changes: tuple[ClaimChangeView, ...]


@dataclass(frozen=True)
class IndexErrorView:
    artifact_path: str
    error_code: str
    error_label: str
    message: str
    file_modified_at: str
    recorded_at: str


LANE_ORDER = ("technical", "fundamental", "news", "synthesis")
LANE_LABELS = {
    "technical": "기술 분석",
    "fundamental": "펀더멘털",
    "news": "뉴스 검토",
    "synthesis": "통합 판단",
}
SCENARIO_ORDER = ("bull", "base", "bear")
SCENARIO_LABELS = {"bull": "상승", "base": "기준", "bear": "하락"}
EXCHANGE_LABELS = {"KRX": "한국거래소"}
STOCK_DISPLAY_NAMES = {
    ("KRX", "000660"): "SK하이닉스",
    ("KRX", "005930"): "삼성전자",
    ("KRX", "035420"): "네이버",
    ("KRX", "035720"): "카카오",
    ("NASDAQ", "AAPL"): "애플",
    ("NASDAQ", "AMZN"): "아마존",
    ("NASDAQ", "MSFT"): "마이크로소프트",
    ("NASDAQ", "NFLX"): "넷플릭스",
    ("NYSE", "BE"): "블룸에너지",
    ("NYSE", "SPOT"): "스포티파이",
}
TIMEFRAME_LABELS = {"1d": "일봉", "1w": "주봉", "1mo": "월봉"}
HORIZON_LABELS = {"1-3 months": "1~3개월"}
CURRENCY_LABELS = {"KRW": "원", "USD": "미국 달러"}
REVIEW_LABELS = {"pass": "통과", "fail": "반려"}
SOURCE_TYPE_LABELS = {
    "market_data_provider_api": "시장 데이터 제공사 API",
    "market_data_provider": "시장 데이터 제공사",
    "secondary_market_data": "보조 시장 데이터",
    "issuer_press_release_primary": "기업 공식 보도자료",
    "issuer_ir_primary": "기업 공식 실적자료",
    "regulatory_filing_primary": "공식 규제 공시",
    "government_primary": "정부 공식 자료",
    "reuters_republication": "로이터 재게시 기사",
    "joint_official_announcement": "공동 공식 발표",
    "industry_research": "산업 조사자료",
    "fixture": "검증용 자료",
}
ANALYST_STANCE_LABELS = {
    "constructive": "긍정적",
    "balanced": "균형",
    "cautious": "신중",
}
ANALYST_CONFIDENCE_LABELS = {"high": "높음", "medium": "보통", "low": "낮음"}
PERSPECTIVE_ORDER = ("technical", "fundamental", "news", "risk")
PERSPECTIVE_LABELS = {
    "technical": "기술적 관점",
    "fundamental": "펀더멘털 관점",
    "news": "뉴스·시장 관점",
    "risk": "반대 관점",
}
PERSPECTIVE_IMPACT_LABELS = {
    "supportive": "긍정 기여",
    "mixed": "혼재",
    "cautionary": "주의 요인",
}
INDEX_ERROR_LABELS = {
    "read_error": "파일 읽기 실패",
    "json_error": "데이터 형식 오류",
    "validation_error": "검증 실패",
    "duplicate_run_id": "실행 ID 중복",
    "index_error": "인덱싱 실패",
}


def format_kst(value: datetime | None, pattern: str) -> str:
    if value is None:
        return "—"
    return value.astimezone(SEOUL).strftime(pattern)


def exchange_label(value: str) -> str:
    return EXCHANGE_LABELS.get(value, value)


def stock_display_name(exchange: str, ticker: str) -> str:
    return STOCK_DISPLAY_NAMES.get((exchange.upper(), ticker.upper()), ticker)


def timeframe_label(value: str) -> str:
    return TIMEFRAME_LABELS.get(value, value)


def horizon_label(value: str) -> str:
    return HORIZON_LABELS.get(value, value)


def to_analysis_row(run: AnalysisRun) -> AnalysisRow:
    return AnalysisRow(
        run_id=run.run_id,
        ticker=run.ticker,
        display_name=stock_display_name(run.exchange, run.ticker),
        exchange=run.exchange,
        exchange_label=exchange_label(run.exchange),
        timeframe=run.timeframe,
        timeframe_label=timeframe_label(run.timeframe),
        horizon=run.horizon,
        horizon_label=horizon_label(run.horizon),
        as_of_date=format_kst(run.as_of, "%Y.%m.%d"),
        as_of_time=format_kst(run.as_of, "%H:%M 한국시간"),
        source_count=run.source_count,
        claim_count=run.claim_count,
        review_verdict=run.review_verdict,
        review_verdict_label=REVIEW_LABELS.get(run.review_verdict, run.review_verdict),
        report_available=run.report_path is not None,
    )


def _safe_external_url(value: str) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _source_view(source: Source, claim_ids: list[str]) -> SourceView:
    return SourceView(
        source_id=source.source_id,
        title=source.title,
        url=_safe_external_url(source.url),
        published_at=format_kst(source.published_at, "%Y.%m.%d"),
        retrieved_at=format_kst(source.retrieved_at, "%Y.%m.%d %H:%M 한국시간"),
        source_type=SOURCE_TYPE_LABELS.get(source.source_type, source.source_type),
        claim_ids=tuple(sorted(claim_ids)),
    )


def _format_reviewed_at(value: object) -> str:
    if not isinstance(value, str):
        return "—"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    return format_kst(parsed, "%Y.%m.%d %H:%M 한국시간")


def _analyst_report_view(evidence: dict[str, object]) -> AnalystReportView | None:
    report = evidence.get("analyst_report")
    if not isinstance(report, dict):
        return None

    raw_key_points = report.get("key_points", [])
    key_points = tuple(
        AnalystKeyPointView(
            title=str(item["title"]),
            assessment=str(item["assessment"]),
            claim_ids=tuple(item.get("claim_ids", [])),
        )
        for item in raw_key_points
        if isinstance(item, dict)
    )

    raw_perspectives = report.get("perspectives", {})
    perspectives: list[AnalystPerspectiveView] = []
    if isinstance(raw_perspectives, dict):
        for name in PERSPECTIVE_ORDER:
            item = raw_perspectives.get(name)
            if not isinstance(item, dict):
                continue
            impact = str(item.get("impact", "mixed"))
            perspectives.append(
                AnalystPerspectiveView(
                    name=name,
                    label=PERSPECTIVE_LABELS[name],
                    impact=impact,
                    impact_label=PERSPECTIVE_IMPACT_LABELS.get(impact, impact),
                    conclusion=str(item.get("conclusion", "")),
                    claim_ids=tuple(item.get("claim_ids", [])),
                )
            )

    raw_monitoring = report.get("monitoring_points", [])
    monitoring_points = tuple(
        AnalystMonitoringView(
            signal=str(item["signal"]),
            interpretation=str(item["interpretation"]),
            claim_ids=tuple(item.get("claim_ids", [])),
        )
        for item in raw_monitoring
        if isinstance(item, dict)
    )
    final_assessment = report.get("final_assessment", {})
    if not isinstance(final_assessment, dict):
        final_assessment = {}
    stance = str(report.get("stance", "balanced"))
    confidence = str(report.get("confidence", "medium"))
    return AnalystReportView(
        stance=stance,
        stance_label=ANALYST_STANCE_LABELS.get(stance, stance),
        confidence=confidence,
        confidence_label=ANALYST_CONFIDENCE_LABELS.get(confidence, confidence),
        headline=str(report.get("headline", "")),
        summary=str(report.get("summary", "")),
        key_points=key_points,
        perspectives=tuple(perspectives),
        monitoring_points=monitoring_points,
        final_assessment=str(final_assessment.get("text", "")),
        final_claim_ids=tuple(final_assessment.get("claim_ids", [])),
    )


def to_analysis_detail(run: AnalysisRun) -> AnalysisDetail:
    evidence = run.evidence_json
    source_claim_ids: dict[str, list[str]] = {source.source_id: [] for source in run.sources}
    for claim in run.claims:
        for link in claim.source_links:
            source_claim_ids.setdefault(link.source_id, []).append(claim.claim_id)

    sources = tuple(
        _source_view(source, source_claim_ids.get(source.source_id, []))
        for source in sorted(run.sources, key=lambda item: item.source_id)
    )
    source_map = {source.source_id: source for source in sources}

    claims_by_lane: dict[str, list[ClaimView]] = {lane: [] for lane in LANE_ORDER}
    for claim in sorted(run.claims, key=lambda item: item.claim_id):
        lane = claim.lane or "synthesis"
        claim_sources = tuple(
            source_map[link.source_id]
            for link in sorted(claim.source_links, key=lambda item: item.source_id)
            if link.source_id in source_map
        )
        claims_by_lane.setdefault(lane, []).append(
            ClaimView(
                claim_id=claim.claim_id,
                lane=lane,
                kind=claim.kind,
                kind_label="사실" if claim.kind == "fact" else "추론",
                text=claim.text,
                confidence=f"{round(claim.confidence * 100)}%",
                sources=claim_sources,
            )
        )

    analysis_lanes = evidence.get("analyses", {})
    lanes: list[LaneView] = []
    for lane_name in LANE_ORDER:
        lane_claims = tuple(claims_by_lane.get(lane_name, []))
        if lane_name == "synthesis" and not lane_claims:
            continue
        lane_data = analysis_lanes.get(lane_name, {})
        status = lane_data.get("status", "complete" if lane_claims else "omitted")
        lanes.append(
            LaneView(
                name=lane_name,
                label=LANE_LABELS.get(lane_name, lane_name),
                status=status,
                status_label="완료" if status == "complete" else "생략",
                reason=lane_data.get("reason"),
                claims=lane_claims,
            )
        )

    scenario_data = evidence.get("scenarios", {})
    scenario_map = {scenario.scenario_name: scenario for scenario in run.scenarios}
    scenarios: list[ScenarioView] = []
    for name in SCENARIO_ORDER:
        scenario = scenario_map.get(name)
        if scenario is None:
            continue
        raw_scenario = scenario_data.get(name, {})
        scenarios.append(
            ScenarioView(
                name=name,
                label=SCENARIO_LABELS[name],
                thesis=scenario.thesis,
                triggers=tuple(
                    trigger.text
                    for trigger in sorted(scenario.triggers, key=lambda item: item.position)
                ),
                invalidation=scenario.invalidation,
                claim_ids=tuple(raw_scenario.get("claim_ids", [])),
            )
        )

    review = evidence.get("review", {})
    return AnalysisDetail(
        run_id=run.run_id,
        ticker=run.ticker,
        display_name=stock_display_name(run.exchange, run.ticker),
        exchange=run.exchange,
        exchange_label=exchange_label(run.exchange),
        currency=run.currency,
        currency_label=CURRENCY_LABELS.get(run.currency, run.currency),
        timeframe=run.timeframe,
        timeframe_label=timeframe_label(run.timeframe),
        horizon=run.horizon,
        horizon_label=horizon_label(run.horizon),
        as_of_date=format_kst(run.as_of, "%Y.%m.%d"),
        as_of_time=format_kst(run.as_of, "%H:%M 한국시간"),
        review_verdict=run.review_verdict.upper(),
        review_verdict_label=REVIEW_LABELS.get(run.review_verdict, run.review_verdict),
        reviewed_at=_format_reviewed_at(review.get("reviewed_at")),
        order_action=str(evidence.get("order_action", "none")),
        source_count=run.source_count,
        claim_count=run.claim_count,
        report_available=run.report_path is not None,
        analyst_report=_analyst_report_view(evidence),
        scenarios=tuple(scenarios),
        lanes=tuple(lanes),
        sources=sources,
        conflicts=tuple(
            conflict.text for conflict in sorted(run.conflicts, key=lambda item: item.position)
        ),
        limitations=tuple(
            limitation.text
            for limitation in sorted(run.limitations, key=lambda item: item.position)
        ),
    )


def _count_change(before: int, after: int) -> str:
    difference = after - before
    if difference > 0:
        return f"+{difference}"
    if difference < 0:
        return str(difference)
    return "변화 없음"


def to_analysis_comparison(
    before_run: AnalysisRun, after_run: AnalysisRun
) -> AnalysisComparisonView:
    before = to_analysis_detail(before_run)
    after = to_analysis_detail(after_run)
    before_stance = before.analyst_report.stance_label if before.analyst_report else "—"
    after_stance = after.analyst_report.stance_label if after.analyst_report else "—"
    metrics = (
        ComparisonMetricView(
            "분석 기준일",
            before.as_of_date,
            after.as_of_date,
            "갱신",
        ),
        ComparisonMetricView(
            "애널리스트 판단",
            before_stance,
            after_stance,
            "변경" if before_stance != after_stance else "유지",
        ),
        ComparisonMetricView(
            "원자 주장",
            str(before.claim_count),
            str(after.claim_count),
            _count_change(before.claim_count, after.claim_count),
        ),
        ComparisonMetricView(
            "출처",
            str(before.source_count),
            str(after.source_count),
            _count_change(before.source_count, after.source_count),
        ),
    )

    before_scenarios = {scenario.name: scenario for scenario in before.scenarios}
    after_scenarios = {scenario.name: scenario for scenario in after.scenarios}
    scenarios = tuple(
        ScenarioComparisonView(
            name=name,
            label=SCENARIO_LABELS[name],
            before=before_scenarios[name].thesis,
            after=after_scenarios[name].thesis,
            changed=before_scenarios[name].thesis != after_scenarios[name].thesis,
        )
        for name in SCENARIO_ORDER
        if name in before_scenarios and name in after_scenarios
    )

    before_claims = {claim.claim_id: claim.text for claim in before_run.claims}
    after_claims = {claim.claim_id: claim.text for claim in after_run.claims}
    claim_changes: list[ClaimChangeView] = []
    for claim_id in sorted(after_claims.keys() - before_claims.keys()):
        claim_changes.append(
            ClaimChangeView("added", "추가", claim_id, None, after_claims[claim_id])
        )
    for claim_id in sorted(before_claims.keys() - after_claims.keys()):
        claim_changes.append(
            ClaimChangeView("removed", "제외", claim_id, before_claims[claim_id], None)
        )
    for claim_id in sorted(before_claims.keys() & after_claims.keys()):
        if before_claims[claim_id] != after_claims[claim_id]:
            claim_changes.append(
                ClaimChangeView(
                    "changed",
                    "수정",
                    claim_id,
                    before_claims[claim_id],
                    after_claims[claim_id],
                )
            )
    return AnalysisComparisonView(
        before=before,
        after=after,
        metrics=metrics,
        scenarios=scenarios,
        claim_changes=tuple(claim_changes),
    )


def to_index_error_view(error: IndexError) -> IndexErrorView:
    return IndexErrorView(
        artifact_path=error.artifact_path,
        error_code=error.error_code,
        error_label=INDEX_ERROR_LABELS.get(error.error_code, error.error_code),
        message=error.message,
        file_modified_at=format_kst(error.file_modified_at, "%Y.%m.%d %H:%M 한국시간"),
        recorded_at=format_kst(error.recorded_at, "%Y.%m.%d %H:%M 한국시간"),
    )
