#!/usr/bin/env python3
"""Compatibility entry point for the project-owned evidence validator."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pipeline.evidence_validator import main, validate_artifact  # noqa: E402,F401


if __name__ == "__main__":
    raise SystemExit(main())
