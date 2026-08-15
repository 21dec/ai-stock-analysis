from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.publish_stock_pages import (
    AutomationConfig,
    PublishError,
    StockConfig,
    build_publication,
    commit_pages,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "evals" / "cases" / "valid-stock-analysis.json"
PAGES_TEMPLATE = REPO_ROOT / "templates" / "pages-index-template.html"


def _config() -> AutomationConfig:
    return AutomationConfig(
        timeframe="1d",
        horizon="1-3 months",
        pages_base_url="https://example.github.io/reports/",
        stocks=(
            StockConfig(
                ticker="TEST",
                exchange="TEST-EXCHANGE",
                currency="USD",
                display_name="테스트 기업",
                order=0,
            ),
        ),
    )


class PublishStockPagesTests(unittest.TestCase):
    def test_build_is_validated_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary)
            artifacts_root = repo_root / "artifacts" / "runs"
            run_directory = artifacts_root / "fixture-run"
            run_directory.mkdir(parents=True)
            (run_directory / "evidence.json").write_text(
                FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            docs_root = repo_root / "docs"

            with patch("scripts.publish_stock_pages._tracked_report_paths", return_value=[]):
                first, latest, managed = build_publication(
                    repo_root, artifacts_root, docs_root, _config(), PAGES_TEMPLATE
                )
                second, _, _ = build_publication(
                    repo_root, artifacts_root, docs_root, _config(), PAGES_TEMPLATE
                )

            self.assertEqual(first.status, "changed")
            self.assertEqual(first.validated_artifacts, 1)
            self.assertEqual(first.published_reports, 1)
            self.assertEqual(second.status, "unchanged")
            self.assertEqual(len(latest), 1)
            self.assertIn("docs/index.html", managed)
            self.assertIn("docs/reports/TEST-2026-08-14.html", managed)
            self.assertTrue((run_directory / "TEST-2026-08-14.html").is_file())
            self.assertTrue((docs_root / "reports" / "TEST-2026-08-14.html").is_file())
            index = (docs_root / "index.html").read_text(encoding="utf-8")
            self.assertIn("테스트 기업", index)
            self.assertIn("1~3개월", index)

    def test_invalid_artifact_blocks_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary)
            artifacts_root = repo_root / "artifacts" / "runs"
            run_directory = artifacts_root / "invalid-run"
            run_directory.mkdir(parents=True)
            artifact = json.loads(FIXTURE.read_text(encoding="utf-8"))
            artifact["order_action"] = "buy"
            (run_directory / "evidence.json").write_text(
                json.dumps(artifact), encoding="utf-8"
            )

            with patch("scripts.publish_stock_pages._tracked_report_paths", return_value=[]):
                with self.assertRaises(PublishError):
                    build_publication(
                        repo_root,
                        artifacts_root,
                        repo_root / "docs",
                        _config(),
                        PAGES_TEMPLATE,
                    )
            self.assertFalse((repo_root / "docs" / "index.html").exists())

    def test_commit_stages_only_managed_pages_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary)
            docs_root = repo_root / "docs"
            docs_root.mkdir()
            managed = docs_root / "index.html"
            managed.write_text("<title>관리 파일</title>", encoding="utf-8")
            unrelated = docs_root / "개인메모.txt"
            unrelated.write_text("커밋되면 안 됨", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"], cwd=repo_root, check=True
            )

            commit = commit_pages(repo_root, docs_root, ["docs/index.html"], "테스트 커밋")

            self.assertIsNotNone(commit)
            tracked = subprocess.run(
                ["git", "ls-files"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertEqual(tracked, ["docs/index.html"])
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()
