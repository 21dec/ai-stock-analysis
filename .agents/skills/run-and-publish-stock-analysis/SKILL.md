---
name: run-and-publish-stock-analysis
description: Run the configured stock watchlist through governed graph analysis, deterministic validation, local PostgreSQL synchronization, static report generation, GitHub Pages indexing, git publication, and public URL verification. Use when Codex must automate recurring stock research, refresh every configured stock, publish validated reports, or execute the complete analysis-to-GitHub-Pages workflow without manual handoffs.
---

# Run And Publish Stock Analysis

Execute the configured watchlist from research through public verification. Treat evidence files as the source of truth and static HTML/PostgreSQL as derived outputs.

## Required inputs

1. Read `config/stock-automation.json` from the project root.
2. Read the complete `../run-stock-analysis-graph/SKILL.md` and every policy it requires.
3. Read [references/automation-contract.md](references/automation-contract.md) before publishing or diagnosing a failed run.

Do not continue if the configuration is missing, duplicated, or contains no enabled stocks.

## Workflow

1. Determine the latest completed regular-market session separately for KRX and US exchanges. Never use intraday data as a completed daily close.
2. Check `artifacts/runs/` for an already validated run with the same ticker, timeframe, horizon, and market-session date. Reuse it when no newer completed session exists.
3. Analyze every stock that needs a refresh with `run-stock-analysis-graph`.
   - Use up to three parallel subagents and assign disjoint artifact directories.
   - Keep technical, fundamental, news, adversarial review, synthesis, and deterministic validation gates.
   - Write Korean `analyst_report` content and schema 1.1 evidence.
   - Require `review.verdict=pass`, `order_action=none`, and complete bull/base/bear trigger and invalidation fields.
   - Never create or suggest an order.
4. For Kakao-group securities, do not access Kakao-owned domains. Use DART, KIND, KRX, regulatory filings, and independent public sources.
5. After every required stock has a valid artifact, run:

   ```bash
   PYTHONPATH=. .venv/bin/python scripts/publish_stock_pages.py \
     --sync-db --commit --push --verify
   ```

6. Report the analyzed, reused, published, committed, pushed, and publicly verified counts. Include the GitHub Pages index URL.

## Hard gates

- Stop before publication when any enabled stock lacks valid evidence.
- Stop before commit when any artifact fails deterministic validation.
- Stop before commit when unrelated files are staged.
- Publish only the explicitly managed `docs/index.html` and canonical `docs/reports/<TICKER>-<YYYY-MM-DD>.html` files.
- Treat an unchanged run as success; do not create an empty commit.
- Consider publication complete only when the public index contains every latest report link and each link returns HTTP 200.
- Retry transient Pages propagation until the script timeout. Do not weaken validation to make a run pass.

## Recovery

- Research failure: preserve completed artifact lanes, retry the failed stock at most twice, then report the exact blocker.
- Database failure: do not commit or push; repair local synchronization first.
- Git divergence or unrelated staged files: stop and report; never force-push or reset user changes.
- Pages timeout after a successful push: keep the commit, report deployment verification as incomplete, and verify again later.
