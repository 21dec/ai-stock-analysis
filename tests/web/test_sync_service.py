from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from my_stock_web.indexer import SyncResult
from my_stock_web.sync_service import ArtifactSyncService


class ArtifactSyncServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_immediately_and_repeats_at_interval(self):
        calls: list[Path] = []

        def fake_sync(_session_factory, artifacts_root: Path) -> SyncResult:
            calls.append(artifacts_root)
            return SyncResult(scanned=1, unchanged=1)

        service = ArtifactSyncService(
            object(),
            Path("/tmp/test-artifacts"),
            interval_seconds=0.01,
            sync_function=fake_sync,
        )

        await service.start()
        await asyncio.sleep(0.035)
        await service.stop()

        snapshot = service.snapshot()
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(snapshot.state, "idle")
        self.assertEqual(snapshot.last_result["scanned"], 1)
        self.assertIsNotNone(snapshot.next_sync_at)

    async def test_keeps_last_error_without_stopping_service(self):
        def broken_sync(_session_factory, _artifacts_root: Path) -> SyncResult:
            raise RuntimeError("동기화 실패")

        service = ArtifactSyncService(
            object(),
            Path("/tmp/test-artifacts"),
            interval_seconds=60,
            sync_function=broken_sync,
        )

        await service.sync_now()

        snapshot = service.snapshot()
        self.assertEqual(snapshot.state, "error")
        self.assertEqual(snapshot.last_error, "동기화 실패")


if __name__ == "__main__":
    unittest.main()
