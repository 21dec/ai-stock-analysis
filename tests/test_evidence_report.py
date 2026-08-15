import contextlib
import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from scripts.generate_evidence_report import main
from scripts.pipeline.evidence_report import (
    EvidenceValidationError,
    render_evidence_report,
    report_filename,
    write_report,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class EvidenceReportTests(unittest.TestCase):
    def load_fixture(self, name="valid-stock-analysis.json"):
        path = REPO_ROOT / "evals" / "cases" / name
        return json.loads(path.read_text(encoding="utf-8"))

    def test_report_filename_uses_ticker_and_as_of_date(self):
        self.assertEqual(report_filename(self.load_fixture()), "TEST-2026-08-14.html")

    def test_render_includes_scenarios_and_escapes_dynamic_text(self):
        artifact = self.load_fixture()
        artifact["claims"][0]["text"] = "<script>alert('x')</script>"
        artifact["analyst_report"]["summary"] = "<img src=x onerror=alert(1)>"

        html = render_evidence_report(artifact)

        self.assertIn("상승·기준·하락 경로", html)
        self.assertIn("검증된 주식 분석", html)
        self.assertIn("상승 시나리오", html)
        self.assertIn("수석 애널리스트 브리핑", html)
        self.assertIn("근거는 유효하지만 방향 확인이 필요한 검증용 판단", html)
        self.assertIn("관점별 종합", html)
        self.assertIn("판단을 바꿀 신호", html)
        self.assertIn("완료", html)
        self.assertNotIn("Governed equity analysis", html)
        self.assertNotIn("BULL CASE", html)
        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert('x')</script>", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)
        self.assertNotIn("<img src=x onerror=alert(1)>", html)

    def test_invalid_artifact_never_renders(self):
        with self.assertRaises(EvidenceValidationError):
            render_evidence_report(self.load_fixture("invalid-stock-analysis.json"))

    def test_write_report_does_not_overwrite_different_content_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.html"
            output.write_text("old", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                write_report("new", output)

            self.assertEqual(output.read_text(encoding="utf-8"), "old")


class GenerateEvidenceReportCliTests(unittest.TestCase):
    def test_valid_artifact_writes_report(self):
        fixture = REPO_ROOT / "evals" / "cases" / "valid-stock-analysis.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.html"
            stdout = StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main([str(fixture), "--output", str(output)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())
            self.assertEqual(json.loads(stdout.getvalue())["status"], "created")

    def test_invalid_artifact_does_not_write_report(self):
        fixture = REPO_ROOT / "evals" / "cases" / "invalid-stock-analysis.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.html"
            stdout = StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main([str(fixture), "--output", str(output)])

            self.assertEqual(exit_code, 2)
            self.assertFalse(output.exists())
            self.assertEqual(json.loads(stdout.getvalue())["status"], "validation_failed")


if __name__ == "__main__":
    unittest.main()
