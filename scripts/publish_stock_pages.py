#!/usr/bin/env python3
"""Validate stock artifacts, publish static reports, and optionally deploy GitHub Pages."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path
from string import Template
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pipeline.evidence_report import (  # noqa: E402
    EvidenceValidationError,
    render_evidence_report,
    report_filename,
    write_report,
)

EXCHANGE_LABELS = {
    "KRX": "한국거래소",
    "NASDAQ": "나스닥",
    "NYSE": "뉴욕증권거래소",
}
STANCE_LABELS = {"constructive": "긍정적", "balanced": "균형", "cautious": "신중"}
CONFIDENCE_LABELS = {"high": "높음", "medium": "보통", "low": "낮음"}
HORIZON_LABELS = {"1-3 months": "1~3개월"}
LEGACY_FILENAME = re.compile(
    r"^(?P<ticker>[A-Za-z0-9._-]+)-(?P<date>\d{4}(?:-?\d{2}){2})\.html$"
)


class PublishError(RuntimeError):
    """Raised when the publication gate cannot be crossed safely."""


@dataclass(frozen=True)
class StockConfig:
    ticker: str
    exchange: str
    currency: str
    display_name: str
    order: int

    @property
    def key(self) -> tuple[str, str]:
        return self.exchange, self.ticker


@dataclass(frozen=True)
class AutomationConfig:
    timeframe: str
    horizon: str
    pages_base_url: str
    stocks: tuple[StockConfig, ...]


@dataclass(frozen=True)
class ReportEntry:
    ticker: str
    exchange: str
    display_name: str
    as_of: date
    href: str
    headline: str
    stance: str
    confidence: str
    order: int

    @property
    def stock_key(self) -> tuple[str, str]:
        return self.exchange, self.ticker


@dataclass
class PublishResult:
    status: str
    validated_artifacts: int
    published_reports: int
    latest_reports: int
    history_reports: int
    changed_paths: list[str]
    database_synced: bool = False
    commit: str | None = None
    pushed: bool = False
    pages_verified: bool = False


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublishError(f"JSON을 읽을 수 없습니다: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublishError(f"JSON 최상위 값은 객체여야 합니다: {path}")
    return value


def load_config(path: Path) -> AutomationConfig:
    raw = _read_json(path)
    if raw.get("schema_version") != "1.0":
        raise PublishError("자동화 설정 schema_version은 1.0이어야 합니다.")
    raw_stocks = raw.get("stocks")
    if not isinstance(raw_stocks, list) or not raw_stocks:
        raise PublishError("자동화 설정에 stocks가 필요합니다.")

    stocks: list[StockConfig] = []
    seen: set[tuple[str, str]] = set()
    for order, item in enumerate(raw_stocks):
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        try:
            stock = StockConfig(
                ticker=str(item["ticker"]).upper(),
                exchange=str(item["exchange"]).upper(),
                currency=str(item["currency"]).upper(),
                display_name=str(item["display_name"]).strip(),
                order=order,
            )
        except KeyError as exc:
            raise PublishError(f"종목 설정 필드가 없습니다: {exc.args[0]}") from exc
        if not stock.display_name:
            raise PublishError(f"종목명이 비어 있습니다: {stock.ticker}")
        if stock.key in seen:
            raise PublishError(f"종목 설정이 중복되었습니다: {stock.exchange}:{stock.ticker}")
        seen.add(stock.key)
        stocks.append(stock)
    if not stocks:
        raise PublishError("활성화된 종목이 없습니다.")

    pages_base_url = str(raw.get("pages_base_url", "")).strip()
    if not pages_base_url.startswith("https://"):
        raise PublishError("pages_base_url은 https:// 주소여야 합니다.")
    return AutomationConfig(
        timeframe=str(raw.get("timeframe", "1d")),
        horizon=str(raw.get("horizon", "1-3 months")),
        pages_base_url=pages_base_url.rstrip("/") + "/",
        stocks=tuple(stocks),
    )


def discover_evidence(artifacts_root: Path) -> list[Path]:
    return sorted(path for path in artifacts_root.glob("*/evidence.json") if path.is_file())


def _parse_as_of(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PublishError(f"as_of에 시간대가 없습니다: {value}")
    return parsed


def _atomic_write(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
    return True


def _git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"git {' '.join(args)} 실패: {detail}")
    return result


def _tracked_report_paths(repo_root: Path, docs_root: Path) -> list[Path]:
    relative_docs = docs_root.resolve().relative_to(repo_root.resolve())
    result = _git(repo_root, "ls-files", f"{relative_docs.as_posix()}/reports/*.html")
    return [repo_root / line for line in result.stdout.splitlines() if line.strip()]


def _legacy_entry(
    path: Path, docs_root: Path, stocks: tuple[StockConfig, ...]
) -> ReportEntry | None:
    match = LEGACY_FILENAME.fullmatch(path.name)
    if not match:
        return None
    ticker = match.group("ticker").upper()
    raw_date = match.group("date").replace("-", "")
    try:
        report_date = datetime.strptime(raw_date, "%Y%m%d").date()
    except ValueError:
        return None
    candidates = [stock for stock in stocks if stock.ticker == ticker]
    if len(candidates) != 1:
        return None
    stock = candidates[0]
    return ReportEntry(
        ticker=ticker,
        exchange=stock.exchange,
        display_name=stock.display_name,
        as_of=report_date,
        href=path.resolve().relative_to(docs_root.resolve()).as_posix(),
        headline="기존 공개 보고서",
        stance="legacy",
        confidence="",
        order=stock.order,
    )


def _render_card(entry: ReportEntry) -> str:
    stance_label = STANCE_LABELS[entry.stance]
    confidence_label = CONFIDENCE_LABELS[entry.confidence]
    stance_class = " constructive" if entry.stance == "constructive" else ""
    market = EXCHANGE_LABELS.get(entry.exchange, entry.exchange)
    searchable = f"{entry.display_name} {entry.ticker}"
    return (
        f'<article class="report-card" data-name="{escape(searchable, quote=True)}" '
        f'data-market="{escape(entry.exchange, quote=True)}">'
        f'<div class="report-meta"><span>{escape(market)} · {escape(entry.ticker)}</span>'
        f'<time>{entry.as_of.strftime("%Y.%m.%d")}</time></div>'
        f'<span class="stance{stance_class}">{escape(stance_label)} · '
        f'{escape(confidence_label)}</span><h3>{escape(entry.display_name)}</h3>'
        f'<p>{escape(entry.headline)}</p><a href="{escape(entry.href, quote=True)}">'
        "보고서 읽기 →</a></article>"
    )


def _render_history_row(entry: ReportEntry) -> str:
    market = EXCHANGE_LABELS.get(entry.exchange, entry.exchange)
    searchable = f"{entry.display_name} {entry.ticker}"
    return (
        f'<article class="history-row" data-name="{escape(searchable, quote=True)}" '
        f'data-market="{escape(entry.exchange, quote=True)}">'
        f'<strong>{escape(entry.display_name)}</strong><span>{escape(market)} · '
        f'{escape(entry.ticker)}</span><time>{entry.as_of.strftime("%Y.%m.%d")}</time>'
        f'<a href="{escape(entry.href, quote=True)}">열기 →</a></article>'
    )


def render_pages_index(
    template_path: Path,
    entries: list[ReportEntry],
    horizon: str,
) -> tuple[str, list[ReportEntry], list[ReportEntry]]:
    if not entries:
        raise PublishError("게시할 보고서가 없습니다.")
    unique: dict[str, ReportEntry] = {}
    for entry in entries:
        unique.setdefault(entry.href, entry)
    records = list(unique.values())

    latest_by_stock: dict[tuple[str, str], ReportEntry] = {}
    for entry in records:
        current = latest_by_stock.get(entry.stock_key)
        if current is None or (entry.as_of, entry.href) > (current.as_of, current.href):
            latest_by_stock[entry.stock_key] = entry
    latest = sorted(latest_by_stock.values(), key=lambda item: item.order)
    latest_hrefs = {entry.href for entry in latest}
    history = sorted(
        (entry for entry in records if entry.href not in latest_hrefs),
        key=lambda item: (item.as_of, -item.order, item.href),
        reverse=True,
    )

    newest = max(entry.as_of for entry in records).strftime("%Y.%m.%d")
    template = Template(template_path.read_text(encoding="utf-8"))
    html = template.substitute(
        REPORT_COUNT=str(len(records)),
        STOCK_COUNT=str(len(latest_by_stock)),
        LATEST_DATE=newest,
        HORIZON=escape(HORIZON_LABELS.get(horizon, horizon)),
        LATEST_CARDS="\n          ".join(_render_card(entry) for entry in latest),
        HISTORY_ROWS=(
            "\n          ".join(_render_history_row(entry) for entry in history)
            if history
            else '<p class="empty" style="display:block">이전 보고서가 없습니다.</p>'
        ),
    )
    return html, latest, history


def build_publication(
    repo_root: Path,
    artifacts_root: Path,
    docs_root: Path,
    config: AutomationConfig,
    pages_template: Path,
) -> tuple[PublishResult, list[ReportEntry], list[str]]:
    catalog = {stock.key: stock for stock in config.stocks}
    evidence_paths = discover_evidence(artifacts_root)
    entries: list[ReportEntry] = []
    changed_paths: list[str] = []
    seen_output: dict[str, Path] = {}
    covered: set[tuple[str, str]] = set()

    for evidence_path in evidence_paths:
        data = _read_json(evidence_path)
        key = str(data.get("exchange", "")).upper(), str(data.get("ticker", "")).upper()
        stock = catalog.get(key)
        if stock is None:
            continue
        if data.get("timeframe") != config.timeframe or data.get("horizon") != config.horizon:
            continue
        try:
            html = render_evidence_report(data)
        except EvidenceValidationError as exc:
            raise PublishError(
                f"검증에 실패한 artifact입니다: {evidence_path}: {'; '.join(exc.result['errors'])}"
            ) from exc

        filename = report_filename(data)
        previous = seen_output.get(filename)
        if previous is not None:
            raise PublishError(
                f"동일 종목·기준일 보고서가 중복되었습니다: {previous} / {evidence_path}"
            )
        seen_output[filename] = evidence_path
        covered.add(key)

        artifact_report = evidence_path.parent / filename
        if write_report(html, artifact_report, force=True):
            changed_paths.append(artifact_report.resolve().relative_to(repo_root.resolve()).as_posix())
        public_report = docs_root / "reports" / filename
        if write_report(html, public_report, force=True):
            changed_paths.append(public_report.resolve().relative_to(repo_root.resolve()).as_posix())

        report = data["analyst_report"]
        entries.append(
            ReportEntry(
                ticker=stock.ticker,
                exchange=stock.exchange,
                display_name=stock.display_name,
                as_of=_parse_as_of(str(data["as_of"])).date(),
                href=f"reports/{filename}",
                headline=str(report["headline"]),
                stance=str(report["stance"]),
                confidence=str(report["confidence"]),
                order=stock.order,
            )
        )

    missing = [stock.display_name for stock in config.stocks if stock.key not in covered]
    if missing:
        raise PublishError("유효한 분석 artifact가 없는 종목: " + ", ".join(missing))

    managed_hrefs = {entry.href for entry in entries}
    for path in _tracked_report_paths(repo_root, docs_root):
        relative = path.resolve().relative_to(docs_root.resolve()).as_posix()
        if relative in managed_hrefs:
            continue
        legacy = _legacy_entry(path, docs_root, config.stocks)
        if legacy is not None:
            entries.append(legacy)

    index_html, latest, history = render_pages_index(pages_template, entries, config.horizon)
    index_path = docs_root / "index.html"
    if _atomic_write(index_path, index_html):
        changed_paths.append(index_path.resolve().relative_to(repo_root.resolve()).as_posix())

    result = PublishResult(
        status="changed" if changed_paths else "unchanged",
        validated_artifacts=len(seen_output),
        published_reports=len({entry.href for entry in entries}),
        latest_reports=len(latest),
        history_reports=len(history),
        changed_paths=sorted(set(changed_paths)),
    )
    docs_prefix = docs_root.resolve().relative_to(repo_root.resolve()).as_posix()
    managed_paths = [f"{docs_prefix}/index.html"] + [
        f"{docs_prefix}/{entry.href}" for entry in entries if entry.stance != "legacy"
    ]
    return result, latest, sorted(set(managed_paths))


def sync_local_database(repo_root: Path, artifacts_root: Path) -> None:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "index_artifacts.py"),
        "--artifacts-root",
        str(artifacts_root),
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(repo_root), str(repo_root / "src"), environment.get("PYTHONPATH", "")]
    )
    result = subprocess.run(
        command,
        cwd=repo_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"로컬 PostgreSQL 동기화 실패: {detail}")


def commit_pages(
    repo_root: Path,
    docs_root: Path,
    managed_paths: list[str],
    commit_message: str,
) -> str | None:
    allowed_prefix = docs_root.resolve().relative_to(repo_root.resolve()).as_posix() + "/"
    allowed = {path for path in managed_paths if path.startswith(allowed_prefix)}
    already_staged = {
        line.strip()
        for line in _git(repo_root, "diff", "--cached", "--name-only").stdout.splitlines()
        if line.strip()
    }
    unrelated = sorted(path for path in already_staged if path not in allowed)
    if unrelated:
        raise PublishError(
            "관련 없는 staged 파일이 있어 커밋을 중단합니다: " + ", ".join(unrelated)
        )

    if allowed:
        _git(repo_root, "add", "--", *sorted(allowed))
    staged = _git(repo_root, "diff", "--cached", "--name-only").stdout.splitlines()
    if not staged:
        return None
    unexpected = sorted(path for path in staged if path not in allowed)
    if unexpected:
        raise PublishError(
            "Pages 외 파일이 staged 되어 커밋을 중단합니다: " + ", ".join(unexpected)
        )
    _git(repo_root, "diff", "--cached", "--check")
    _git(repo_root, "commit", "-m", commit_message)
    return _git(repo_root, "rev-parse", "HEAD").stdout.strip()


def push_pages(repo_root: Path, remote: str, branch: str) -> None:
    current_branch = _git(repo_root, "branch", "--show-current").stdout.strip()
    if current_branch != branch:
        raise PublishError(f"푸시 대상 브랜치가 아닙니다: 현재 {current_branch}, 필요 {branch}")
    _git(repo_root, "push", remote, branch)


def _fetch(url: str) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "my-stock-pages-verifier/1.0"})
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - configured HTTPS URL
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, ""
    except URLError:
        return 0, ""


def verify_pages(
    base_url: str,
    latest: list[ReportEntry],
    timeout_seconds: int,
    interval_seconds: int = 10,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    expected_hrefs = [entry.href for entry in latest]
    while True:
        index_status, index_html = _fetch(base_url)
        index_ready = index_status == 200 and all(href in index_html for href in expected_hrefs)
        reports_ready = index_ready
        if index_ready:
            for href in expected_hrefs:
                status, _ = _fetch(urljoin(base_url, href))
                if status != 200:
                    reports_ready = False
                    break
        if reports_ready:
            return
        if time.monotonic() >= deadline:
            raise PublishError("GitHub Pages가 제한 시간 안에 최신 인덱스를 제공하지 않았습니다.")
        time.sleep(interval_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--artifacts-root", type=Path)
    parser.add_argument("--docs-root", type=Path)
    parser.add_argument("--pages-template", type=Path)
    parser.add_argument("--sync-db", action="store_true")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--verify-timeout", type=int, default=300)
    parser.add_argument("--commit-message")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    config_path = (args.config or repo_root / "config" / "stock-automation.json").resolve()
    artifacts_root = (args.artifacts_root or repo_root / "artifacts" / "runs").resolve()
    docs_root = (args.docs_root or repo_root / "docs").resolve()
    pages_template = (
        args.pages_template or repo_root / "templates" / "pages-index-template.html"
    ).resolve()
    if args.push and not args.commit:
        parser.error("--push에는 --commit이 필요합니다.")

    try:
        config = load_config(config_path)
        result, latest, managed_paths = build_publication(
            repo_root,
            artifacts_root,
            docs_root,
            config,
            pages_template,
        )
        if args.sync_db:
            sync_local_database(repo_root, artifacts_root)
            result.database_synced = True
        if args.commit:
            message = args.commit_message or (
                "주식 분석 보고서 자동 게시: " + date.today().isoformat()
            )
            result.commit = commit_pages(repo_root, docs_root, managed_paths, message)
        if args.push and result.commit is not None:
            push_pages(repo_root, args.remote, args.branch)
            result.pushed = True
        if args.verify:
            verify_pages(config.pages_base_url, latest, args.verify_timeout)
            result.pages_verified = True
    except (PublishError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
