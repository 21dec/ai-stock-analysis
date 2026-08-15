"""Index governed evidence artifacts into the rebuildable PostgreSQL read model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session, sessionmaker

from my_stock_web.models import (
    AnalysisConflict,
    AnalysisLimitation,
    AnalysisRun,
    Claim,
    ClaimSource,
    IndexError,
    Scenario,
    ScenarioTrigger,
    Source,
)
from scripts.pipeline.evidence_validator import validate_artifact

INDEX_LOCK_ID = 21_130_831_503_409_995
LANE_ORDER = ("technical", "fundamental", "news")
IndexStatus = Literal["inserted", "updated", "unchanged", "invalid"]


@dataclass(frozen=True)
class PreparedArtifact:
    path: Path
    relative_path: str
    content_hash: str
    data: dict[str, Any] | None
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class SyncResult:
    scanned: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    invalid: int = 0
    removed: int = 0

    def record(self, status: IndexStatus) -> None:
        setattr(self, status, getattr(self, status) + 1)

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class SyncInProgressError(RuntimeError):
    pass


def discover_artifacts(artifacts_root: Path) -> list[Path]:
    if not artifacts_root.exists():
        return []
    return sorted(path for path in artifacts_root.glob("*/evidence.json") if path.is_file())


def _relative_artifact_path(path: Path, artifacts_root: Path) -> str:
    resolved = path.resolve()
    root = artifacts_root.resolve()
    return resolved.relative_to(root).as_posix()


def _safe_mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def prepare_artifact(path: Path, artifacts_root: Path) -> PreparedArtifact:
    relative_path = _relative_artifact_path(path, artifacts_root)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        return PreparedArtifact(path, relative_path, "", None, "read_error", str(exc))

    content_hash = hashlib.sha256(payload).hexdigest()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return PreparedArtifact(path, relative_path, content_hash, None, "json_error", str(exc))

    validation = validate_artifact(data)
    if not validation["valid"]:
        return PreparedArtifact(
            path,
            relative_path,
            content_hash,
            None,
            "validation_error",
            "; ".join(validation["errors"]),
        )
    return PreparedArtifact(path, relative_path, content_hash, data)


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _lane_by_claim(data: dict[str, Any]) -> dict[str, str]:
    lanes: dict[str, list[str]] = {}
    for lane_name in LANE_ORDER:
        for claim_id in data["analyses"][lane_name].get("claim_ids", []):
            lanes.setdefault(claim_id, []).append(lane_name)
    return {claim_id: "+".join(claim_lanes) for claim_id, claim_lanes in lanes.items()}


def _find_report_path(
    artifact_path: Path, artifacts_root: Path, data: dict[str, Any]
) -> str | None:
    report_date = _parse_timestamp(data["as_of"]).date().isoformat()
    canonical = artifact_path.parent / f"{data['ticker'].upper()}-{report_date}.html"
    if canonical.is_file():
        return canonical.resolve().relative_to(artifacts_root.resolve()).as_posix()
    candidates = sorted(artifact_path.parent.glob("*.html"))
    if not candidates:
        return None
    return candidates[0].resolve().relative_to(artifacts_root.resolve()).as_posix()


def _remove_index_error(session: Session, relative_path: str) -> None:
    session.execute(delete(IndexError).where(IndexError.artifact_path == relative_path))


def _record_index_error(session: Session, prepared: PreparedArtifact) -> None:
    session.execute(delete(AnalysisRun).where(AnalysisRun.artifact_path == prepared.relative_path))
    error = session.get(IndexError, prepared.relative_path)
    if error is None:
        error = IndexError(artifact_path=prepared.relative_path)
        session.add(error)
    error.error_code = prepared.error_code or "unknown_error"
    error.message = prepared.error_message or "Unknown indexing error"
    error.file_modified_at = _safe_mtime(prepared.path)
    error.recorded_at = datetime.now(timezone.utc)


def _insert_children(session: Session, run: AnalysisRun, data: dict[str, Any]) -> None:
    lane_by_claim = _lane_by_claim(data)
    sources = [
        Source(
            run_id=run.run_id,
            source_id=source["id"],
            title=source["title"],
            url=source["url"],
            published_at=_parse_timestamp(source.get("published_at")),
            retrieved_at=_parse_timestamp(source["retrieved_at"]),
            source_type=source["source_type"],
        )
        for source in data["sources"]
    ]
    claims = [
        Claim(
            run_id=run.run_id,
            claim_id=claim["id"],
            lane=lane_by_claim.get(claim["id"]),
            kind=claim["kind"],
            text=claim["text"],
            confidence=float(claim["confidence"]),
        )
        for claim in data["claims"]
    ]
    scenarios = [
        Scenario(
            run_id=run.run_id,
            scenario_name=name,
            thesis=scenario["thesis"],
            invalidation=scenario["invalidation"],
        )
        for name, scenario in data["scenarios"].items()
    ]
    session.add_all([*sources, *claims, *scenarios])
    session.flush()

    session.add_all(
        ClaimSource(run_id=run.run_id, claim_id=claim["id"], source_id=source_id)
        for claim in data["claims"]
        for source_id in claim["source_ids"]
    )
    session.add_all(
        ScenarioTrigger(
            run_id=run.run_id,
            scenario_name=name,
            position=position,
            text=trigger,
        )
        for name, scenario in data["scenarios"].items()
        for position, trigger in enumerate(scenario["triggers"])
    )
    session.add_all(
        AnalysisConflict(run_id=run.run_id, position=position, text=value)
        for position, value in enumerate(data["conflicts"])
    )
    session.add_all(
        AnalysisLimitation(run_id=run.run_id, position=position, text=value)
        for position, value in enumerate(data["limitations"])
    )


def _index_prepared(
    session: Session, prepared: PreparedArtifact, artifacts_root: Path
) -> IndexStatus:
    if prepared.data is None:
        _record_index_error(session, prepared)
        return "invalid"

    data = prepared.data
    existing = session.get(AnalysisRun, data["run_id"])
    if existing is not None and existing.artifact_path != prepared.relative_path:
        collision = PreparedArtifact(
            prepared.path,
            prepared.relative_path,
            prepared.content_hash,
            None,
            "duplicate_run_id",
            f"run_id already belongs to {existing.artifact_path}",
        )
        _record_index_error(session, collision)
        return "invalid"
    if existing is not None and existing.content_hash == prepared.content_hash:
        _remove_index_error(session, prepared.relative_path)
        return "unchanged"

    status: IndexStatus = "updated" if existing is not None else "inserted"
    if existing is not None:
        session.execute(delete(AnalysisRun).where(AnalysisRun.run_id == existing.run_id))
        session.flush()

    run = AnalysisRun(
        run_id=data["run_id"],
        schema_version=data["schema_version"],
        ticker=data["ticker"].upper(),
        exchange=data["exchange"],
        currency=data["currency"],
        timeframe=data["timeframe"],
        horizon=data["horizon"],
        as_of=_parse_timestamp(data["as_of"]),
        review_verdict=data["review"]["verdict"],
        source_count=len(data["sources"]),
        claim_count=len(data["claims"]),
        artifact_path=prepared.relative_path,
        report_path=_find_report_path(prepared.path, artifacts_root, data),
        content_hash=prepared.content_hash,
        evidence_json=data,
        indexed_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.flush()
    _insert_children(session, run, data)
    _remove_index_error(session, prepared.relative_path)
    return status


def sync_artifacts(
    session_factory: sessionmaker[Session], artifacts_root: Path, *, prune_missing: bool = True
) -> SyncResult:
    artifacts_root = artifacts_root.resolve()
    paths = discover_artifacts(artifacts_root)
    result = SyncResult(scanned=len(paths))
    prepared_artifacts = [prepare_artifact(path, artifacts_root) for path in paths]
    discovered = {artifact.relative_path for artifact in prepared_artifacts}

    with session_factory.begin() as session:
        locked = session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"), {"lock_id": INDEX_LOCK_ID}
        )
        if not locked:
            raise SyncInProgressError("another artifact synchronization is already running")

        for prepared in prepared_artifacts:
            try:
                with session.begin_nested():
                    status = _index_prepared(session, prepared, artifacts_root)
                result.record(status)
            except Exception as exc:  # isolate one malformed artifact from the rest of the sync
                failed = PreparedArtifact(
                    prepared.path,
                    prepared.relative_path,
                    prepared.content_hash,
                    None,
                    "index_error",
                    str(exc),
                )
                with session.begin_nested():
                    _record_index_error(session, failed)
                result.record("invalid")

        if prune_missing:
            indexed_paths = set(session.scalars(select(AnalysisRun.artifact_path)))
            missing = indexed_paths - discovered
            if missing:
                deletion = session.execute(
                    delete(AnalysisRun).where(AnalysisRun.artifact_path.in_(missing))
                )
                result.removed = deletion.rowcount or 0

    return result
