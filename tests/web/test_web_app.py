from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete

from my_stock_web.app import create_app
from my_stock_web.config import Settings
from my_stock_web.db import create_database_engine, create_session_factory
from my_stock_web.indexer import sync_artifacts
from my_stock_web.models import AnalysisRun, IndexError

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get("MY_STOCK_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "MY_STOCK_TEST_DATABASE_URL is not configured")
class WebAppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        alembic_config = Config(str(REPO_ROOT / "alembic.ini"))
        with patch.dict(os.environ, {"MY_STOCK_DATABASE_URL": TEST_DATABASE_URL}):
            command.upgrade(alembic_config, "head")

        cls.engine = create_database_engine(
            Settings(
                database_url=TEST_DATABASE_URL,
                project_root=REPO_ROOT,
                artifacts_root=REPO_ROOT / "artifacts" / "runs",
            )
        )
        cls.session_factory = create_session_factory(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.artifacts_root = Path(self.temporary_directory.name)
        run_directory = self.artifacts_root / "web-valid"
        run_directory.mkdir()

        fixture_path = REPO_ROOT / "evals" / "cases" / "valid-stock-analysis.json"
        artifact = json.loads(fixture_path.read_text(encoding="utf-8"))
        artifact["run_id"] = "integration-web-valid"
        (run_directory / "evidence.json").write_text(json.dumps(artifact), encoding="utf-8")
        (run_directory / "TEST-2026-08-14.html").write_text(
            "<!doctype html><title>Test report</title><p>standalone report</p>",
            encoding="utf-8",
        )

        settings = Settings(
            database_url=TEST_DATABASE_URL,
            project_root=REPO_ROOT,
            artifacts_root=self.artifacts_root,
        )
        self.client = TestClient(create_app(settings), raise_server_exceptions=False)
        self.client.__enter__()

    def tearDown(self):
        if self.client is not None:
            self.client.__exit__(None, None, None)
        with self.session_factory.begin() as session:
            session.execute(delete(AnalysisRun).where(AnalysisRun.run_id.like("integration-web-%")))
            session.execute(delete(IndexError).where(IndexError.artifact_path.like("web-%")))
        self.temporary_directory.cleanup()

    def add_second_analysis(self) -> str:
        fixture_path = REPO_ROOT / "evals" / "cases" / "valid-stock-analysis.json"
        artifact = json.loads(fixture_path.read_text(encoding="utf-8"))
        artifact["run_id"] = "integration-web-valid-second"
        artifact["as_of"] = "2026-08-15T15:30:00+09:00"
        artifact["claims"][0]["text"] = "두 번째 실행에서 수정된 테스트 주장이다."
        artifact["analyst_report"]["stance"] = "cautious"
        artifact["analyst_report"]["headline"] = "두 번째 분석에서 달라진 종합 판단"
        artifact["scenarios"]["base"]["thesis"] = "두 번째 실행의 기준 시나리오"
        run_directory = self.artifacts_root / "web-valid-second"
        run_directory.mkdir()
        (run_directory / "evidence.json").write_text(json.dumps(artifact), encoding="utf-8")
        sync_artifacts(self.client.app.state.session_factory, self.artifacts_root)
        return artifact["run_id"]

    def test_dashboard_shows_real_indexed_summary(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("분석은 쌓일수록", response.text)
        self.assertIn("TEST", response.text)
        self.assertIn("1개의 검증된 분석", response.text)
        self.assertIn("나의 주식 분석", response.text)
        self.assertNotIn("PERSONAL RESEARCH ARCHIVE", response.text)
        self.assertNotIn("MY STOCK", response.text)
        self.assertNotIn("fake", response.text.lower())

    def test_history_filters_and_no_results_state(self):
        matching = self.client.get("/analyses", params={"q": "TEST", "exchange": "TEST-EXCHANGE"})
        missing = self.client.get("/analyses", params={"q": "DOES-NOT-EXIST"})

        self.assertEqual(matching.status_code, 200)
        self.assertIn("1개의 분석", matching.text)
        self.assertIn("integration-web-valid", matching.text)
        self.assertIn("조건에 맞는 분석이 없습니다", missing.text)

    def test_invalid_date_is_ignored_with_explanation(self):
        response = self.client.get("/analyses", params={"date_from": "2026-99-99"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("날짜 형식이 올바르지 않아 적용하지 않았습니다", response.text)

    def test_report_route_serves_only_indexed_file(self):
        report = self.client.get("/reports/integration-web-valid")
        missing = self.client.get("/reports/unknown-run")

        self.assertEqual(report.status_code, 200)
        self.assertIn("standalone report", report.text)
        self.assertEqual(missing.status_code, 404)
        self.assertIn("요청을 완료하지 못했습니다", missing.text)

    def test_analysis_detail_traces_scenarios_claims_and_sources(self):
        response = self.client.get("/analyses/integration-web-valid")

        self.assertEqual(response.status_code, 200)
        self.assertIn("검증용 상승 시나리오", response.text)
        self.assertIn("수석 애널리스트 브리핑", response.text)
        self.assertIn("근거는 유효하지만 방향 확인이 필요한 검증용 판단", response.text)
        self.assertIn("관점별 종합", response.text)
        self.assertIn("판단을 바꿀 신호", response.text)
        self.assertIn("검증용 기준 시나리오", response.text)
        self.assertIn("검증용 하락 시나리오", response.text)
        self.assertIn("결정적으로 검증할 수 있는 테스트 주장", response.text)
        self.assertIn("결정적 검증용 출처", response.text)
        self.assertIn("테스트 검증용 자료에 한정", response.text)
        self.assertIn("원본 데이터", response.text)
        self.assertIn("주문 없음", response.text)
        self.assertIn('href="https://example.com/fixture"', response.text)

    def test_analysis_detail_and_stock_timeline_return_404_for_unknown_records(self):
        detail = self.client.get("/analyses/unknown-run")
        timeline = self.client.get("/stocks/KRX/UNKNOWN")

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(timeline.status_code, 404)

    def test_stock_timeline_lists_indexed_runs_and_links_to_detail(self):
        response = self.client.get("/stocks/TEST-EXCHANGE/TEST")

        self.assertEqual(response.status_code, 200)
        self.assertIn("TEST 분석 연대기", response.text)
        self.assertIn("integration-web-valid", response.text)
        self.assertIn("/analyses/integration-web-valid", response.text)
        self.assertIn("두 분석 비교", response.text)

    def test_comparison_requires_two_runs_then_shows_changes(self):
        empty = self.client.get("/stocks/TEST-EXCHANGE/TEST/compare")
        second_run_id = self.add_second_analysis()
        comparison = self.client.get(
            "/stocks/TEST-EXCHANGE/TEST/compare",
            params={"before": "integration-web-valid", "after": second_run_id},
        )

        self.assertEqual(empty.status_code, 200)
        self.assertIn("두 번째 분석이 필요합니다", empty.text)
        self.assertEqual(comparison.status_code, 200)
        self.assertIn("두 번째 분석에서 달라진 종합 판단", comparison.text)
        self.assertIn("두 번째 실행의 기준 시나리오", comparison.text)
        self.assertIn("수정", comparison.text)
        self.assertIn("claim-1", comparison.text)

    def test_system_status_shows_database_sync_and_errors(self):
        response = self.client.get("/system")

        self.assertEqual(response.status_code, 200)
        self.assertIn("시스템 상태", response.text)
        self.assertIn("연결됨", response.text)
        self.assertIn("60초 간격", response.text)
        self.assertIn("인덱싱 오류가 없습니다", response.text)
        self.assertIn('aria-live="polite"', response.text)

    def test_evidence_route_returns_only_indexed_json(self):
        evidence = self.client.get("/artifacts/integration-web-valid/evidence")
        missing = self.client.get("/artifacts/unknown-run/evidence")

        self.assertEqual(evidence.status_code, 200)
        self.assertIn("integration-web-valid", evidence.text)
        self.assertIn("원본 데이터", evidence.text)
        self.assertTrue(evidence.headers["content-type"].startswith("text/html"))
        self.assertEqual(missing.status_code, 404)

    def test_health_reports_database_connection(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "connected")
        self.assertEqual(response.json()["indexed_runs"], 1)
        self.assertEqual(response.json()["sync"], "idle")
        self.assertEqual(response.json()["sync_interval_seconds"], 60)

    def test_empty_artifact_root_has_specific_empty_state(self):
        self.client.__exit__(None, None, None)
        self.client = None
        with tempfile.TemporaryDirectory() as empty_directory:
            settings = Settings(
                database_url=TEST_DATABASE_URL,
                project_root=REPO_ROOT,
                artifacts_root=Path(empty_directory),
            )
            with TestClient(create_app(settings), raise_server_exceptions=False) as client:
                response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("아직 인덱싱된 분석이 없습니다", response.text)

    def test_mobile_styles_use_intentional_reflow(self):
        response = self.client.get("/static/styles.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn("@media (max-width: 760px)", response.text)
        self.assertIn(".analysis-row { display: block", response.text)
        self.assertIn(".scenario-ledger { grid-template-columns: 1fr", response.text)
        self.assertIn(".perspective-grid { grid-template-columns: 1fr", response.text)
        self.assertIn(":focus-visible", response.text)
        self.assertIn(".comparison-picker { grid-template-columns: 1fr", response.text)


if __name__ == "__main__":
    unittest.main()
