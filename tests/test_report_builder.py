import tempfile
import unittest
from pathlib import Path

from scripts.pipeline.report_builder import (
    REQUIRED_CONTEXT_KEYS,
    _TEMPLATE_PATH,
    pages_url,
    render_report,
    report_filename,
    report_path,
)

SAMPLE_CONTEXT = {
    "TICKER": "AAPL",
    "COMPANY": "Apple Inc.",
    "DATE": "2026-08-05",
    "PRICE": "$185.32",
    "WEATHER_ICON": "☀️",
    "WEATHER_SCORE": "82",
    "WEATHER_LABEL": "맑음",
    "SIGNAL": "BULLISH",
    "SIGNAL_CLASS": "bullish",
    "CONFIDENCE": "HIGH",
    "HORIZON": "LONG-TERM",
    "ANALYSIS_BODY_HTML": "<h2>Summary</h2><p>Test body.</p>",
}


class RenderReportTests(unittest.TestCase):
    def test_renders_all_placeholders(self):
        html = render_report(SAMPLE_CONTEXT)
        self.assertIn("AAPL", html)
        self.assertIn("Apple Inc.", html)
        self.assertIn("$185.32", html)
        self.assertIn("82", html)
        self.assertIn('class="badge signal-badge bullish"', html)
        self.assertIn("<h2>Summary</h2><p>Test body.</p>", html)
        # design constraint: no left-border accent styling anywhere
        self.assertNotIn("border-left", html)

    def test_missing_key_raises(self):
        incomplete = dict(SAMPLE_CONTEXT)
        del incomplete["TICKER"]
        with self.assertRaises(ValueError):
            render_report(incomplete)

    def test_required_keys_matches_sample_context(self):
        self.assertEqual(REQUIRED_CONTEXT_KEYS, frozenset(SAMPLE_CONTEXT.keys()))

    def test_required_keys_matches_actual_template_placeholders(self):
        from string import Template

        template_text = _TEMPLATE_PATH.read_text(encoding="utf-8")
        placeholders = set()
        for match in Template.pattern.finditer(template_text):
            name = match.group("named") or match.group("braced")
            if name:
                placeholders.add(name)
        self.assertEqual(REQUIRED_CONTEXT_KEYS, frozenset(placeholders))


class PathHelperTests(unittest.TestCase):
    def test_report_filename(self):
        self.assertEqual(report_filename("aapl", "20260805"), "AAPL-20260805.html")

    def test_report_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            result = report_path("aapl", "20260805", docs_dir)
            self.assertEqual(result, docs_dir / "reports" / "AAPL-20260805.html")

    def test_pages_url_default_repo(self):
        url = pages_url("aapl", "20260805")
        self.assertEqual(
            url, "https://21dec.github.io/ai-stock-analysis/reports/AAPL-20260805.html"
        )

    def test_pages_url_custom_repo(self):
        url = pages_url("tsla", "20260101", repo="someone/other-repo")
        self.assertEqual(
            url, "https://someone.github.io/other-repo/reports/TSLA-20260101.html"
        )


if __name__ == "__main__":
    unittest.main()
