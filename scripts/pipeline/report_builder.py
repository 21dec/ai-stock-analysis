"""Renders the fixed flat/minimal HTML report template and computes the
deterministic file path / GitHub Pages URL for a given ticker + date."""

from pathlib import Path
from string import Template

_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "report-template.html"

REQUIRED_CONTEXT_KEYS = frozenset(
    {
        "TICKER",
        "COMPANY",
        "DATE",
        "PRICE",
        "WEATHER_ICON",
        "WEATHER_SCORE",
        "WEATHER_LABEL",
        "SIGNAL",
        "SIGNAL_CLASS",
        "CONFIDENCE",
        "HORIZON",
        "ANALYSIS_BODY_HTML",
        "CHART_DATA_JSON",
    }
)


def render_report(context: dict, template_path: Path = _TEMPLATE_PATH) -> str:
    missing = REQUIRED_CONTEXT_KEYS - context.keys()
    if missing:
        raise ValueError(f"missing template context keys: {sorted(missing)}")
    template_text = template_path.read_text(encoding="utf-8")
    return Template(template_text).substitute(context)


def report_filename(ticker: str, report_date: str) -> str:
    return f"{ticker.upper()}-{report_date}.html"


def report_path(ticker: str, report_date: str, docs_dir: Path) -> Path:
    return docs_dir / "reports" / report_filename(ticker, report_date)


def pages_url(ticker: str, report_date: str, repo: str = "21dec/ai-stock-analysis") -> str:
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}/reports/{report_filename(ticker, report_date)}"
