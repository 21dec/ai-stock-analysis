import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_report import build_context, main


SAMPLE_INPUT = {
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
    "analysis_body_html": "<h2>Summary</h2><p>Test body.</p>",
}


class BuildContextTests(unittest.TestCase):
    def test_signal_class_lowercased(self):
        from scripts.pipeline.weather_score import compute_weather_score

        weather = compute_weather_score(
            signal_score_10=SAMPLE_INPUT["signal_score_10"],
            confidence=SAMPLE_INPUT["confidence"],
            mtf_alignment_3=SAMPLE_INPUT["mtf_alignment_3"],
            rsi=SAMPLE_INPUT["rsi"],
        )
        context = build_context(SAMPLE_INPUT, weather)
        self.assertEqual(context["SIGNAL_CLASS"], "bullish")
        self.assertEqual(context["TICKER"], "AAPL")
        self.assertEqual(context["ANALYSIS_BODY_HTML"], "<h2>Summary</h2><p>Test body.</p>")


class MainCliTests(unittest.TestCase):
    def test_writes_html_and_prints_json_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            input_path.write_text(json.dumps(SAMPLE_INPUT), encoding="utf-8")
            docs_dir = tmp_path / "docs"

            import io
            import contextlib

            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exit_code = main([str(input_path), "--docs-dir", str(docs_dir)])

            self.assertEqual(exit_code, 0)
            result = json.loads(captured.getvalue())

            expected_report_path = docs_dir / "reports" / "AAPL-20260805.html"
            self.assertEqual(Path(result["report_path"]), expected_report_path)
            self.assertTrue(expected_report_path.exists())

            html = expected_report_path.read_text(encoding="utf-8")
            self.assertIn("AAPL", html)
            self.assertIn("<h2>Summary</h2><p>Test body.</p>", html)

            self.assertEqual(
                result["pages_url"],
                "https://21dec.github.io/ai-stock-analysis/reports/AAPL-20260805.html",
            )
            self.assertIn("AAPL", result["kakao_message"])
            self.assertIn(result["pages_url"], result["kakao_message"])


if __name__ == "__main__":
    unittest.main()
