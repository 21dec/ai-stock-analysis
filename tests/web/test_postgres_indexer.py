from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, inspect, select

from my_stock_web.config import Settings
from my_stock_web.db import create_database_engine, create_session_factory
from my_stock_web.indexer import sync_artifacts
from my_stock_web.models import AnalysisRun, Claim, IndexError, Scenario, Source

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get("MY_STOCK_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "MY_STOCK_TEST_DATABASE_URL is not configured")
class PostgresIndexerIntegrationTests(unittest.TestCase):
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

    def tearDown(self):
        with self.session_factory.begin() as session:
            session.execute(
                delete(AnalysisRun).where(AnalysisRun.run_id.like("integration-test-%"))
            )
            session.execute(delete(IndexError).where(IndexError.artifact_path.like("test-%")))

    def load_fixture(self, name: str) -> dict:
        path = REPO_ROOT / "evals" / "cases" / name
        return json.loads(path.read_text(encoding="utf-8"))

    def test_migration_created_expected_tables(self):
        expected = {
            "analysis_runs",
            "claims",
            "sources",
            "claim_sources",
            "scenarios",
            "scenario_triggers",
            "analysis_conflicts",
            "analysis_limitations",
            "index_errors",
        }
        self.assertTrue(expected.issubset(set(inspect(self.engine).get_table_names())))

    def test_valid_artifact_is_indexed_once(self):
        artifact = self.load_fixture("valid-stock-analysis.json")
        artifact["run_id"] = "integration-test-valid"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_path = root / "test-valid" / "evidence.json"
            artifact_path.parent.mkdir()
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

            first = sync_artifacts(self.session_factory, root, prune_missing=False)
            second = sync_artifacts(self.session_factory, root, prune_missing=False)

        self.assertEqual(first.inserted, 1)
        self.assertEqual(second.unchanged, 1)
        with self.session_factory() as session:
            run = session.get(AnalysisRun, "integration-test-valid")
            self.assertIsNotNone(run)
            self.assertEqual(run.claim_count, 1)
            self.assertEqual(session.scalar(select(func.count()).select_from(Claim)), 1)
            self.assertEqual(session.scalar(select(func.count()).select_from(Source)), 1)
            self.assertEqual(session.scalar(select(func.count()).select_from(Scenario)), 3)

    def test_invalid_artifact_is_recorded_without_analysis_run(self):
        artifact = self.load_fixture("invalid-stock-analysis.json")
        artifact["run_id"] = "integration-test-invalid"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_path = root / "test-invalid" / "evidence.json"
            artifact_path.parent.mkdir()
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

            result = sync_artifacts(self.session_factory, root, prune_missing=False)

        self.assertEqual(result.invalid, 1)
        with self.session_factory() as session:
            self.assertIsNone(session.get(AnalysisRun, "integration-test-invalid"))
            error = session.get(IndexError, "test-invalid/evidence.json")
            self.assertIsNotNone(error)
            self.assertEqual(error.error_code, "validation_error")


if __name__ == "__main__":
    unittest.main()
