"""Application configuration loaded from explicit environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql+psycopg://localhost:5432/my_stock"


@dataclass(frozen=True)
class Settings:
    database_url: str
    project_root: Path
    artifacts_root: Path
    sync_interval_seconds: int = 60

    @classmethod
    def from_env(cls) -> "Settings":
        project_root = Path(os.environ.get("MY_STOCK_PROJECT_ROOT", PROJECT_ROOT)).resolve()
        artifacts_root = Path(
            os.environ.get("MY_STOCK_ARTIFACTS_ROOT", project_root / "artifacts" / "runs")
        ).resolve()
        return cls(
            database_url=os.environ.get("MY_STOCK_DATABASE_URL", DEFAULT_DATABASE_URL),
            project_root=project_root,
            artifacts_root=artifacts_root,
            sync_interval_seconds=max(
                1, int(os.environ.get("MY_STOCK_SYNC_INTERVAL_SECONDS", "60"))
            ),
        )
