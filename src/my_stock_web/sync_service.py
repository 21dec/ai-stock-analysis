"""Application-scoped periodic synchronization for local evidence artifacts."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from my_stock_web.indexer import SyncResult, sync_artifacts

SyncFunction = Callable[[sessionmaker[Session], Path], SyncResult]


@dataclass(frozen=True)
class SyncSnapshot:
    state: str
    interval_seconds: int
    last_started_at: datetime | None
    last_completed_at: datetime | None
    next_sync_at: datetime | None
    last_result: dict[str, int]
    last_error: str | None


class ArtifactSyncService:
    """Run the deterministic artifact indexer immediately and at a fixed interval."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        artifacts_root: Path,
        *,
        interval_seconds: int = 60,
        sync_function: SyncFunction = sync_artifacts,
    ) -> None:
        self.session_factory = session_factory
        self.artifacts_root = artifacts_root
        self.interval_seconds = interval_seconds
        self.sync_function = sync_function
        self.last_started_at: datetime | None = None
        self.last_completed_at: datetime | None = None
        self.next_sync_at: datetime | None = None
        self.last_result: dict[str, int] = SyncResult().to_dict()
        self.last_error: str | None = None
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        await self.sync_now(raise_on_error=True)
        self._task = asyncio.create_task(self._run_loop(), name="artifact-sync-loop")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def sync_now(self, *, raise_on_error: bool = False) -> None:
        if self._lock.locked():
            return
        async with self._lock:
            self._running = True
            self.last_started_at = datetime.now(timezone.utc)
            try:
                result = await asyncio.to_thread(
                    self.sync_function, self.session_factory, self.artifacts_root
                )
            except Exception as exc:
                self.last_error = str(exc)
                if raise_on_error:
                    raise
            else:
                self.last_result = result.to_dict()
                self.last_error = None
            finally:
                self.last_completed_at = datetime.now(timezone.utc)
                self.next_sync_at = self.last_completed_at + timedelta(
                    seconds=self.interval_seconds
                )
                self._running = False

    def snapshot(self) -> SyncSnapshot:
        state = "running" if self._running else "error" if self.last_error else "idle"
        return SyncSnapshot(
            state=state,
            interval_seconds=self.interval_seconds,
            last_started_at=self.last_started_at,
            last_completed_at=self.last_completed_at,
            next_sync_at=self.next_sync_at,
            last_result=self.last_result.copy(),
            last_error=self.last_error,
        )

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            await self.sync_now()
