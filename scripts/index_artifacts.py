#!/usr/bin/env python3
"""Synchronize governed stock-analysis artifacts into local PostgreSQL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from my_stock_web.config import Settings  # noqa: E402
from my_stock_web.db import create_database_engine, create_session_factory  # noqa: E402
from my_stock_web.indexer import SyncInProgressError, sync_artifacts  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    defaults = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-root", type=Path, default=defaults.artifacts_root)
    args = parser.parse_args(argv)

    engine = create_database_engine(defaults)
    try:
        result = sync_artifacts(create_session_factory(engine), args.artifacts_root)
    except SyncInProgressError as exc:
        print(json.dumps({"status": "busy", "error": str(exc)}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        engine.dispose()

    print(json.dumps({"status": "ok", **result.to_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
