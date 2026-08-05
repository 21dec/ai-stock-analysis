"""CLI entrypoint: reads a JSON analysis payload, computes the investment
weather score, renders the fixed HTML report, writes it to disk, and prints
the report path / GitHub Pages URL / KakaoTalk message as JSON.

This script does NOT git add/commit/push and does NOT send the KakaoTalk
message itself — those remain explicit agent actions (see PIPELINE.md).
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.pipeline.kakao_message import build_kakao_message
from scripts.pipeline.report_builder import pages_url, render_report, report_path
from scripts.pipeline.weather_score import WeatherResult, compute_weather_score

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_context(data: dict, weather: WeatherResult) -> dict:
    return {
        "TICKER": data["ticker"].upper(),
        "COMPANY": data["company"],
        "DATE": data["date"],
        "PRICE": data["price"],
        "WEATHER_ICON": weather.icon,
        "WEATHER_SCORE": str(weather.score),
        "WEATHER_LABEL": weather.label,
        "SIGNAL": data["signal"],
        "SIGNAL_CLASS": data["signal"].lower(),
        "CONFIDENCE": data["confidence"],
        "HORIZON": data["horizon"],
        "ANALYSIS_BODY_HTML": data["analysis_body_html"],
        "CHART_DATA_JSON": json.dumps(data["chart"], ensure_ascii=False),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate a stock analysis HTML report.")
    parser.add_argument("input_json", help="Path to a JSON file describing the analysis.")
    parser.add_argument(
        "--docs-dir",
        default=str(REPO_ROOT / "docs"),
        help="Docs directory that is the GitHub Pages source (default: <repo>/docs).",
    )
    parser.add_argument(
        "--repo",
        default="21dec/ai-stock-analysis",
        help="GitHub owner/repo used to build the Pages URL.",
    )
    args = parser.parse_args(argv)

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    weather = compute_weather_score(
        signal_score_10=data["signal_score_10"],
        confidence=data["confidence"],
        mtf_alignment_3=data["mtf_alignment_3"],
        rsi=data["rsi"],
    )

    context = build_context(data, weather)
    html = render_report(context)

    docs_dir = Path(args.docs_dir)
    output_path = report_path(data["ticker"], data["date"], docs_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    url = pages_url(data["ticker"], data["date"], repo=args.repo)
    message = build_kakao_message(
        ticker=data["ticker"].upper(),
        company=data["company"],
        price=data["price"],
        weather=weather,
        url=url,
    )

    result = {
        "report_path": str(output_path),
        "pages_url": url,
        "kakao_message": message,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
