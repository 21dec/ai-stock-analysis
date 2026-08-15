"""Deterministic validation for governed stock-analysis evidence artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "run_id",
    "ticker",
    "exchange",
    "currency",
    "timeframe",
    "horizon",
    "as_of",
    "sources",
    "claims",
    "analyses",
    "scenarios",
    "conflicts",
    "review",
    "limitations",
    "order_action",
}
SCHEMA_VERSIONS = {"1.0", "1.1"}
ANALYSIS_LANES = {"technical", "fundamental", "news"}
SCENARIO_NAMES = {"bull", "base", "bear"}
ANALYST_STANCES = {"constructive", "balanced", "cautious"}
ANALYST_CONFIDENCE = {"high", "medium", "low"}
PERSPECTIVE_NAMES = {"technical", "fundamental", "news", "risk"}
PERSPECTIVE_IMPACTS = {"supportive", "mixed", "cautionary"}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _timezone_aware(value: Any) -> bool:
    if not _is_nonempty_string(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _valid_http_url(value: Any) -> bool:
    if not _is_nonempty_string(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _unknown_ids(values: Any, known_ids: set[str], field: str, errors: list[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{field} must be an array")
        return
    invalid = [value for value in values if not _is_nonempty_string(value)]
    if invalid:
        errors.append(f"{field} must contain only non-empty string ids")
    unknown = sorted(
        {value for value in values if isinstance(value, str) and value not in known_ids}
    )
    if unknown:
        errors.append(f"{field} contains unknown ids: {', '.join(unknown)}")


def _validate_analyst_report(report: Any, claim_ids: set[str], errors: list[str]) -> None:
    if not isinstance(report, dict):
        errors.append("analyst_report must be an object")
        return

    for field in ("headline", "summary"):
        if not _is_nonempty_string(report.get(field)):
            errors.append(f"analyst_report.{field} must be a non-empty string")
    if report.get("stance") not in ANALYST_STANCES:
        errors.append("analyst_report.stance must be 'constructive', 'balanced', or 'cautious'")
    if report.get("confidence") not in ANALYST_CONFIDENCE:
        errors.append("analyst_report.confidence must be 'high', 'medium', or 'low'")

    key_points = report.get("key_points")
    if not isinstance(key_points, list) or len(key_points) < 2:
        errors.append("analyst_report.key_points must contain at least two items")
    else:
        for index, item in enumerate(key_points):
            prefix = f"analyst_report.key_points[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field in ("title", "assessment"):
                if not _is_nonempty_string(item.get(field)):
                    errors.append(f"{prefix}.{field} must be a non-empty string")
            refs = item.get("claim_ids")
            if not isinstance(refs, list) or not refs:
                errors.append(f"{prefix}.claim_ids must be a non-empty array")
            else:
                _unknown_ids(refs, claim_ids, f"{prefix}.claim_ids", errors)

    perspectives = report.get("perspectives")
    if not isinstance(perspectives, dict):
        errors.append("analyst_report.perspectives must be an object")
    else:
        missing = sorted(PERSPECTIVE_NAMES - perspectives.keys())
        if missing:
            errors.append("analyst_report.perspectives is missing: " + ", ".join(missing))
        for name in sorted(PERSPECTIVE_NAMES & perspectives.keys()):
            item = perspectives[name]
            prefix = f"analyst_report.perspectives.{name}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if item.get("impact") not in PERSPECTIVE_IMPACTS:
                errors.append(f"{prefix}.impact must be 'supportive', 'mixed', or 'cautionary'")
            if not _is_nonempty_string(item.get("conclusion")):
                errors.append(f"{prefix}.conclusion must be a non-empty string")
            refs = item.get("claim_ids")
            if not isinstance(refs, list) or not refs:
                errors.append(f"{prefix}.claim_ids must be a non-empty array")
            else:
                _unknown_ids(refs, claim_ids, f"{prefix}.claim_ids", errors)

    monitoring_points = report.get("monitoring_points")
    if not isinstance(monitoring_points, list) or len(monitoring_points) < 2:
        errors.append("analyst_report.monitoring_points must contain at least two items")
    else:
        for index, item in enumerate(monitoring_points):
            prefix = f"analyst_report.monitoring_points[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field in ("signal", "interpretation"):
                if not _is_nonempty_string(item.get(field)):
                    errors.append(f"{prefix}.{field} must be a non-empty string")
            refs = item.get("claim_ids")
            if not isinstance(refs, list) or not refs:
                errors.append(f"{prefix}.claim_ids must be a non-empty array")
            else:
                _unknown_ids(refs, claim_ids, f"{prefix}.claim_ids", errors)

    final_assessment = report.get("final_assessment")
    if not isinstance(final_assessment, dict):
        errors.append("analyst_report.final_assessment must be an object")
    else:
        if not _is_nonempty_string(final_assessment.get("text")):
            errors.append("analyst_report.final_assessment.text must be a non-empty string")
        refs = final_assessment.get("claim_ids")
        if not isinstance(refs, list) or not refs:
            errors.append("analyst_report.final_assessment.claim_ids must be a non-empty array")
        else:
            _unknown_ids(refs, claim_ids, "analyst_report.final_assessment.claim_ids", errors)


def validate_artifact(data: Any) -> dict[str, Any]:
    """Return a stable validation result without mutating the artifact."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return {
            "valid": False,
            "errors": ["root must be a JSON object"],
            "warnings": [],
            "metrics": {},
        }

    missing = sorted(REQUIRED_TOP_LEVEL - data.keys())
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")

    if data.get("schema_version") not in SCHEMA_VERSIONS:
        errors.append("schema_version must be '1.0' or '1.1'")

    for field in (
        "schema_version",
        "run_id",
        "ticker",
        "exchange",
        "currency",
        "timeframe",
        "horizon",
    ):
        if field in data and not _is_nonempty_string(data[field]):
            errors.append(f"{field} must be a non-empty string")

    if "as_of" in data and not _timezone_aware(data["as_of"]):
        errors.append("as_of must be an ISO 8601 timestamp with timezone")

    if data.get("order_action") != "none":
        errors.append("order_action must be 'none'")

    sources = data.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
        sources = []

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = source.get("id")
        if not _is_nonempty_string(source_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif source_id in source_ids:
            errors.append(f"duplicate source id: {source_id}")
        else:
            source_ids.add(source_id)
        if not _is_nonempty_string(source.get("title")):
            errors.append(f"{prefix}.title must be a non-empty string")
        if not _valid_http_url(source.get("url")):
            errors.append(f"{prefix}.url must be an http(s) URL")
        if not _is_nonempty_string(source.get("source_type")):
            errors.append(f"{prefix}.source_type must be a non-empty string")
        if not _timezone_aware(source.get("retrieved_at")):
            errors.append(f"{prefix}.retrieved_at must include a timezone")
        published_at = source.get("published_at")
        if published_at is not None and not _timezone_aware(published_at):
            errors.append(f"{prefix}.published_at must include a timezone when present")

    claims = data.get("claims", [])
    if not isinstance(claims, list) or not claims:
        errors.append("claims must be a non-empty array")
        claims = []

    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be an object")
            continue
        claim_id = claim.get("id")
        if not _is_nonempty_string(claim_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif claim_id in claim_ids:
            errors.append(f"duplicate claim id: {claim_id}")
        else:
            claim_ids.add(claim_id)
        if not _is_nonempty_string(claim.get("text")):
            errors.append(f"{prefix}.text must be a non-empty string")
        if claim.get("kind") not in {"fact", "inference"}:
            errors.append(f"{prefix}.kind must be 'fact' or 'inference'")
        confidence = claim.get("confidence")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            errors.append(f"{prefix}.confidence must be a number from 0 to 1")
        refs = claim.get("source_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{prefix}.source_ids must be a non-empty array")
        else:
            _unknown_ids(refs, source_ids, f"{prefix}.source_ids", errors)

    if data.get("schema_version") == "1.1":
        if "analyst_report" not in data:
            errors.append("analyst_report is required for schema_version '1.1'")
        else:
            _validate_analyst_report(data["analyst_report"], claim_ids, errors)

    analyses = data.get("analyses", {})
    if not isinstance(analyses, dict):
        errors.append("analyses must be an object")
        analyses = {}
    missing_lanes = sorted(ANALYSIS_LANES - analyses.keys())
    if missing_lanes:
        errors.append(f"missing analysis lanes: {', '.join(missing_lanes)}")
    for lane in sorted(ANALYSIS_LANES & analyses.keys()):
        analysis = analyses[lane]
        if not isinstance(analysis, dict):
            errors.append(f"analyses.{lane} must be an object")
            continue
        status = analysis.get("status")
        if status not in {"complete", "omitted"}:
            errors.append(f"analyses.{lane}.status must be 'complete' or 'omitted'")
        if status == "omitted" and not _is_nonempty_string(analysis.get("reason")):
            errors.append(f"analyses.{lane}.reason is required when omitted")
        _unknown_ids(analysis.get("claim_ids", []), claim_ids, f"analyses.{lane}.claim_ids", errors)

    scenarios = data.get("scenarios", {})
    if not isinstance(scenarios, dict):
        errors.append("scenarios must be an object")
        scenarios = {}
    missing_scenarios = sorted(SCENARIO_NAMES - scenarios.keys())
    if missing_scenarios:
        errors.append(f"missing scenarios: {', '.join(missing_scenarios)}")
    for name in sorted(SCENARIO_NAMES & scenarios.keys()):
        scenario = scenarios[name]
        if not isinstance(scenario, dict):
            errors.append(f"scenarios.{name} must be an object")
            continue
        if not _is_nonempty_string(scenario.get("thesis")):
            errors.append(f"scenarios.{name}.thesis must be a non-empty string")
        triggers = scenario.get("triggers")
        if (
            not isinstance(triggers, list)
            or not triggers
            or not all(_is_nonempty_string(item) for item in triggers)
        ):
            errors.append(f"scenarios.{name}.triggers must contain non-empty strings")
        if not _is_nonempty_string(scenario.get("invalidation")):
            errors.append(f"scenarios.{name}.invalidation must be a non-empty string")
        refs = scenario.get("claim_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"scenarios.{name}.claim_ids must be a non-empty array")
        else:
            _unknown_ids(refs, claim_ids, f"scenarios.{name}.claim_ids", errors)

    if "conflicts" in data and not isinstance(data["conflicts"], list):
        errors.append("conflicts must be an array")

    review = data.get("review", {})
    if not isinstance(review, dict):
        errors.append("review must be an object")
    else:
        if review.get("verdict") not in {"pass", "fail"}:
            errors.append("review.verdict must be 'pass' or 'fail'")
        if review.get("verdict") != "pass":
            errors.append("review.verdict must be 'pass' before rendering")
        if not isinstance(review.get("issues"), list):
            errors.append("review.issues must be an array")
        if not _timezone_aware(review.get("reviewed_at")):
            errors.append("review.reviewed_at must include a timezone")

    limitations = data.get("limitations")
    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(_is_nonempty_string(item) for item in limitations)
    ):
        errors.append("limitations must contain at least one non-empty limitation")

    metrics = {
        "source_count": len(sources),
        "claim_count": len(claims),
        "scenario_count": len(SCENARIO_NAMES & scenarios.keys()),
    }
    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="Path to the evidence JSON artifact")
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"valid": False, "errors": [str(exc)], "warnings": [], "metrics": {}}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = validate_artifact(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
