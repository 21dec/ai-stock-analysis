"""Render validated evidence artifacts as deterministic, self-contained HTML."""

from __future__ import annotations

import re
from datetime import datetime
from html import escape
from pathlib import Path
from string import Template
from typing import Any

from scripts.pipeline.evidence_validator import validate_artifact

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE_PATH = REPO_ROOT / "templates" / "evidence-report-template.html"
SCENARIO_ORDER = ("bull", "base", "bear")
SCENARIO_LABELS = {"bull": "상승", "base": "기준", "bear": "하락"}
LANE_ORDER = ("technical", "fundamental", "news")
LANE_LABELS = {"technical": "기술", "fundamental": "펀더멘털", "news": "뉴스"}
STATUS_LABELS = {"complete": "완료", "omitted": "생략"}
KIND_LABELS = {"fact": "사실", "inference": "추론"}
EXCHANGE_LABELS = {"KRX": "한국거래소"}
TIMEFRAME_LABELS = {"1d": "일봉", "1w": "주봉", "1mo": "월봉"}
HORIZON_LABELS = {"1-3 months": "1~3개월"}
CURRENCY_LABELS = {"KRW": "원", "USD": "미국 달러"}
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


class EvidenceValidationError(ValueError):
    """Raised when an evidence artifact cannot cross the rendering gate."""

    def __init__(self, result: dict[str, Any]):
        self.result = result
        super().__init__("; ".join(result["errors"]))


def _date_from_as_of(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()


def _safe_filename_part(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    if not normalized:
        raise ValueError("ticker does not contain a filename-safe character")
    return normalized.upper()


def report_filename(data: dict[str, Any]) -> str:
    """Return the canonical report filename for an evidence artifact."""
    return f"{_safe_filename_part(data['ticker'])}-{_date_from_as_of(data['as_of'])}.html"


def _list_html(items: list[str], empty_text: str = "없음") -> str:
    if not items:
        return f'<p class="empty">{escape(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _render_lanes(data: dict[str, Any]) -> str:
    claims_by_id = {claim["id"]: claim for claim in data["claims"]}
    cards: list[str] = []
    for lane_name in LANE_ORDER:
        lane = data["analyses"][lane_name]
        claim_ids = lane.get("claim_ids", [])
        fact_count = sum(claims_by_id[item]["kind"] == "fact" for item in claim_ids)
        inference_count = sum(claims_by_id[item]["kind"] == "inference" for item in claim_ids)
        reason = ""
        if lane["status"] == "omitted":
            reason = f'<p class="muted">{escape(lane["reason"])}</p>'
        cards.append(
            '<article class="lane">'
            f'<span class="status {escape(lane["status"])}">'
            f"{escape(STATUS_LABELS.get(lane['status'], lane['status']))}</span>"
            f"<h3>{LANE_LABELS[lane_name]}</h3>"
            f"<strong>{len(claim_ids)}</strong>"
            f"<small>개 주장 · 사실 {fact_count} · 추론 {inference_count}</small>"
            f"{reason}</article>"
        )
    return "".join(cards)


def _render_scenarios(data: dict[str, Any]) -> str:
    cards: list[str] = []
    for name in SCENARIO_ORDER:
        scenario = data["scenarios"][name]
        triggers = "".join(f"<li>{escape(item)}</li>" for item in scenario["triggers"])
        claim_refs = ", ".join(escape(item) for item in scenario["claim_ids"])
        cards.append(
            f'<article class="scenario {name}">'
            f'<p class="kicker">{SCENARIO_LABELS[name]} 시나리오</p>'
            f"<h3>{SCENARIO_LABELS[name]}</h3>"
            f'<p class="thesis">{escape(scenario["thesis"])}</p>'
            f"<h4>확인 조건</h4><ul>{triggers}</ul>"
            f"<h4>무효화</h4><p>{escape(scenario['invalidation'])}</p>"
            f'<p class="refs">근거 주장: {claim_refs}</p>'
            "</article>"
        )
    return "".join(cards)


def _claim_refs(claim_ids: list[str]) -> str:
    return " ".join(f"<code>{escape(claim_id)}</code>" for claim_id in claim_ids)


def _render_analyst_report(data: dict[str, Any]) -> str:
    report = data.get("analyst_report")
    if not isinstance(report, dict):
        return ""

    stance = str(report["stance"])
    confidence = str(report["confidence"])
    key_points = "".join(
        '<article class="key-point">'
        f'<span class="number">{index:02d}</span>'
        f"<h3>{escape(item['title'])}</h3>"
        f"<p>{escape(item['assessment'])}</p>"
        f'<div class="analyst-refs">근거 {_claim_refs(item["claim_ids"])}</div>'
        "</article>"
        for index, item in enumerate(report["key_points"], start=1)
    )
    perspectives = "".join(
        f'<article class="perspective impact-{escape(report["perspectives"][name]["impact"])}">'
        "<header>"
        f"<h3>{PERSPECTIVE_LABELS[name]}</h3>"
        f"<span>{PERSPECTIVE_IMPACT_LABELS[report['perspectives'][name]['impact']]}</span>"
        "</header>"
        f"<p>{escape(report['perspectives'][name]['conclusion'])}</p>"
        f'<div class="analyst-refs">근거 '
        f"{_claim_refs(report['perspectives'][name]['claim_ids'])}</div>"
        "</article>"
        for name in PERSPECTIVE_ORDER
    )
    monitoring = "".join(
        "<li>"
        f'<span class="number">{index:02d}</span>'
        f"<div><h3>{escape(item['signal'])}</h3>"
        f"<p>{escape(item['interpretation'])}</p></div>"
        f'<div class="analyst-refs">근거 {_claim_refs(item["claim_ids"])}</div>'
        "</li>"
        for index, item in enumerate(report["monitoring_points"], start=1)
    )
    final_assessment = report["final_assessment"]
    return (
        '<section class="analyst-report">'
        '<p class="eyebrow">수석 애널리스트 브리핑</p><h2>종합 의견</h2>'
        '<article class="analyst-lead">'
        '<div class="analyst-verdict">'
        f'<span class="stance stance-{escape(stance)}">현재 판단 · '
        f"{ANALYST_STANCE_LABELS[stance]}</span>"
        f"<span>확신 수준 · {ANALYST_CONFIDENCE_LABELS[confidence]}</span></div>"
        f"<h3>{escape(report['headline'])}</h3>"
        f"<p>{escape(report['summary'])}</p>"
        "</article>"
        f'<div class="key-points">{key_points}</div>'
        '<div class="report-subhead"><h3>관점별 종합</h3>'
        "<p>각 분석이 최종 판단에 미친 영향입니다.</p></div>"
        f'<div class="perspectives">{perspectives}</div>'
        '<div class="report-subhead"><h3>판단을 바꿀 신호</h3>'
        "<p>다음 분석에서 우선 확인할 항목입니다.</p></div>"
        f'<ol class="monitoring">{monitoring}</ol>'
        '<aside class="final-assessment"><span>최종 판단</span>'
        f"<p>{escape(final_assessment['text'])}</p>"
        f'<div class="analyst-refs">근거 '
        f"{_claim_refs(final_assessment['claim_ids'])}</div></aside>"
        "</section>"
    )


def _render_claims(data: dict[str, Any]) -> str:
    source_by_id = {source["id"]: source for source in data["sources"]}
    rows: list[str] = []
    for claim in data["claims"]:
        links = ", ".join(
            f'<a href="{escape(source_by_id[source_id]["url"], quote=True)}" '
            f'target="_blank" rel="noreferrer">{escape(source_id)}</a>'
            for source_id in claim["source_ids"]
        )
        rows.append(
            "<tr>"
            f"<td><code>{escape(claim['id'])}</code></td>"
            f'<td><span class="kind {escape(claim["kind"])}">'
            f"{escape(KIND_LABELS.get(claim['kind'], claim['kind']))}</span></td>"
            f'<td class="claim-text">{escape(claim["text"])}</td>'
            f"<td>{round(claim['confidence'] * 100)}%</td>"
            f"<td>{links}</td>"
            "</tr>"
        )
    return "".join(rows)


def _render_sources(data: dict[str, Any]) -> str:
    items: list[str] = []
    for source in data["sources"]:
        published = source.get("published_at", "발행일 미기재")
        items.append(
            "<li>"
            f'<a href="{escape(source["url"], quote=True)}" target="_blank" rel="noreferrer">'
            f"{escape(source['title'])}</a>"
            f"<span><code>{escape(source['id'])}</code> · "
            f"{escape(source['source_type'])} · {escape(published)}</span>"
            "</li>"
        )
    return "".join(items)


def render_evidence_report(
    data: dict[str, Any], template_path: Path = DEFAULT_TEMPLATE_PATH
) -> str:
    """Validate and render an artifact. Invalid artifacts never reach the template."""
    validation = validate_artifact(data)
    if not validation["valid"]:
        raise EvidenceValidationError(validation)

    template = Template(template_path.read_text(encoding="utf-8"))
    review = data["review"]
    return template.substitute(
        TITLE=f"{escape(data['ticker'])} 주식 분석",
        TICKER=escape(data["ticker"]),
        EXCHANGE=escape(EXCHANGE_LABELS.get(data["exchange"], data["exchange"])),
        CURRENCY=escape(CURRENCY_LABELS.get(data["currency"], data["currency"])),
        TIMEFRAME=escape(TIMEFRAME_LABELS.get(data["timeframe"], data["timeframe"])),
        HORIZON=escape(HORIZON_LABELS.get(data["horizon"], data["horizon"])),
        AS_OF=escape(data["as_of"]),
        RUN_ID=escape(data["run_id"]),
        REVIEWED_AT=escape(review["reviewed_at"]),
        SOURCE_COUNT=str(validation["metrics"]["source_count"]),
        CLAIM_COUNT=str(validation["metrics"]["claim_count"]),
        ANALYST_REPORT=_render_analyst_report(data),
        LANE_CARDS=_render_lanes(data),
        SCENARIO_CARDS=_render_scenarios(data),
        CLAIM_ROWS=_render_claims(data),
        CONFLICTS_HTML=_list_html(data["conflicts"], "기록된 충돌 없음"),
        LIMITATIONS_HTML=_list_html(data["limitations"]),
        SOURCE_ITEMS=_render_sources(data),
    )


def write_report(html: str, output_path: Path, *, force: bool = False) -> bool:
    """Write atomically. Return False when an identical report already exists."""
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        if existing == html:
            return False
        if not force:
            raise FileExistsError(f"refusing to overwrite different report: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(html, encoding="utf-8")
    temporary.replace(output_path)
    return True
