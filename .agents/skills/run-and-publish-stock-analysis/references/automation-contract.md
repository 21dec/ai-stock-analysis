# Automation contract

## Configuration

`config/stock-automation.json` is the watchlist and publishing configuration.

- `timeframe`: artifact timeframe accepted for publication.
- `horizon`: artifact horizon accepted for publication.
- `pages_base_url`: HTTPS URL used for post-push verification.
- `stocks`: ordered list of enabled ticker, exchange, currency, and Korean display name values.

Keep identifiers uppercase. Disable a stock with `"enabled": false`; do not delete historical reports.

## Artifact contract

Each analysis lives at `artifacts/runs/<run-id>/evidence.json`. The evidence must pass `scripts.pipeline.evidence_validator.validate_artifact`. The publisher generates the canonical sibling report and copies it to `docs/reports/<TICKER>-<YYYY-MM-DD>.html`.

Publication fails when two artifacts resolve to the same ticker and market-session date. Produce one final run per ticker and session.

## Publisher

`scripts/publish_stock_pages.py` performs these deterministic steps:

1. Load and validate the watchlist.
2. Select matching evidence artifacts only.
3. Validate and render every configured stock report.
4. Preserve tracked legacy reports while excluding unrelated untracked files.
5. Generate the searchable GitHub Pages index from report metadata.
6. Optionally synchronize local PostgreSQL.
7. Stage only managed Pages files, skip empty commits, and push `main`.
8. Poll the public index until it contains all latest report links and every report returns HTTP 200.

Default post-analysis command:

```bash
PYTHONPATH=. .venv/bin/python scripts/publish_stock_pages.py \
  --sync-db --commit --push --verify
```

Run without flags to regenerate and inspect files locally without database, git, or network side effects.

## Scheduled execution

The local Codex automation runs at 07:30 Asia/Seoul on weekdays. This time follows the completed US session and precedes the Korean open. Market holidays may reuse the previous validated session and must not create an empty commit.

## Success result

The command prints JSON. Success requires `status` to be `changed` or `unchanged`; `database_synced=true` when requested; `pushed=true` when a commit was created; and `pages_verified=true` after public verification. A null commit on an unchanged run is expected.
