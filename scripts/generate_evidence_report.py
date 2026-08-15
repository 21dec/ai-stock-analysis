#!/usr/bin/env python3
"""Generate a deterministic HTML report from a governed evidence artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pipeline.evidence_report import (  # noqa: E402
    EvidenceValidationError,
    render_evidence_report,
    report_filename,
    write_report,
)


def _print_result(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="Path to evidence.json")
    parser.add_argument("--output", type=Path, help="Output HTML path; defaults beside the artifact")
    parser.add_argument("--force", action="store_true", help="Replace a different existing report")
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.artifact.read_text(encoding="utf-8"))
        html = render_evidence_report(data)
        output_path = args.output or args.artifact.parent / report_filename(data)
        created = write_report(html, output_path, force=args.force)
    except EvidenceValidationError as exc:
        _print_result({"status": "validation_failed", **exc.result})
        return 2
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        _print_result({"status": "error", "error": str(exc)})
        return 1

    _print_result(
        {
            "status": "created" if created else "unchanged",
            "report_path": str(output_path.resolve()),
            "run_id": data["run_id"],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
