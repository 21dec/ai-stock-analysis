---
name: run-stock-analysis-graph
description: Run an evidence-backed stock analysis as a governed graph of independent research, technical and fundamental analysis, news review, adversarial review, deterministic validation, and reporting. Use for requests to analyze, compare, monitor, score, or write a report about a stock, ETF, or listed company when current market data, citations, scenarios, or risk checks matter. Do not use to place trades or provide personalized investment instructions.
---

# Run Stock Analysis Graph

Build an inspectable evidence artifact first. Produce prose or HTML only after validation.

## Output language

- Write every user-facing narrative value in Korean, including source titles, claims, scenario theses, triggers, invalidations, conflicts, limitations, and report copy.
- Keep schema keys, stable IDs, ticker and exchange codes unchanged. Retain an unavoidable official proper noun or technical abbreviation only when translating it would reduce accuracy.
- Translate an English source title into a faithful Korean title while preserving its original URL.

## Load policy

- Read `references/analysis-policy.md` before collecting evidence or drafting analysis.
- Read `references/risk-policy.md` before any external publication, messaging, or transaction-adjacent request.

## Execute the graph

1. **Scope**
   - Resolve ticker, exchange, currency, timeframe, analysis horizon, and as-of time.
   - State safe defaults instead of silently guessing.
   - Keep `order_action` equal to `none` throughout this workflow.

2. **Collect evidence**
   - Prefer primary sources for filings, company statements, and exchange data.
   - Use current sources for prices, indicators, news, and market conditions.
   - Give each source and claim a stable ID. Link every factual claim to one or more source IDs.
   - Record both publication time, when available, and retrieval time.

3. **Run independent lanes**
   - Run technical, fundamental, and news/event analysis independently when all are relevant.
   - Delegate lanes to subagents only when they are bounded and do not need concurrent writes.
   - Ask each lane to return claims and evidence, not polished conclusions.
   - Omit an inapplicable lane explicitly rather than inventing data.

4. **Synthesize scenarios**
   - Reconcile conflicting claims without hiding disagreement.
   - Produce an `analyst_report` that reads like a senior analyst briefing: headline, balanced summary, key points, four perspective conclusions, monitoring points, and a final assessment.
   - Link every key point, perspective, monitoring point, and final assessment to existing claim IDs. Never introduce an uncited number or a new fact in the synthesis.
   - Produce bull, base, and bear scenarios.
   - Give every scenario a thesis, observable triggers, and an invalidation condition.

5. **Run adversarial review**
   - Use a reviewer that did not author the main conclusion when practical.
   - Check stale data, unsupported claims, timeframe mismatch, confirmation bias, and scenario asymmetry.
   - Set review verdict to `pass` only after blocking issues are resolved.

6. **Validate**
   - Write the artifact using the schema in `references/analysis-policy.md`.
   - Run `python3 .agents/skills/run-stock-analysis-graph/scripts/validate_evidence.py <artifact.json>`.
   - On failure, return to the responsible node. Retry a node at most twice.
   - After two failed corrections, stop and report the unresolved validation errors.

7. **Render**
   - Draft the user-facing report only from the validated artifact.
   - Render headings, labels, status text, and explanations in Korean.
   - Lead with the analyst briefing. Present scenarios next and preserve atomic claims, sources, conflicts, and limitations as the evidence appendix.
   - Include as-of time, source links, conflicting evidence, three scenarios, invalidations, and limitations.
   - When the artifact also satisfies the existing report input contract, generate HTML with `python3 scripts/generate_report.py <input.json>`.

## Gates

- Do not call a result validated when the validator fails or the review verdict is not `pass`.
- Do not change the validator or fixtures during a run to obtain a pass.
- Pause for explicit user approval before external publication, messaging, deployment, or transaction-related action.
- Never turn analysis into an order as part of this skill.
