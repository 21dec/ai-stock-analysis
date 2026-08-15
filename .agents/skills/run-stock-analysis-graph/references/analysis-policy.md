# Analysis and evidence policy

## Source hierarchy

1. Exchange data, regulatory filings, issuer investor-relations material
2. Reputable market-data providers and official economic data
3. Reputable reporting with a clear publication timestamp
4. Secondary commentary, used only with an explicit limitation

Use current verification for time-sensitive facts. Preserve disagreement between sources. Never use an uncited number in the conclusion.

## Evidence artifact

Store one JSON object with this minimum shape:

```json
{
  "schema_version": "1.1",
  "run_id": "20260814-NVDA-daily",
  "ticker": "NVDA",
  "exchange": "NASDAQ",
  "currency": "USD",
  "timeframe": "1d",
  "horizon": "1-3 months",
  "as_of": "2026-08-14T15:30:00+09:00",
  "sources": [
    {
      "id": "src-1",
      "title": "Source title",
      "url": "https://example.com/source",
      "published_at": "2026-08-14T08:00:00Z",
      "retrieved_at": "2026-08-14T15:20:00+09:00",
      "source_type": "exchange"
    }
  ],
  "claims": [
    {
      "id": "claim-1",
      "text": "A concise factual claim",
      "kind": "fact",
      "source_ids": ["src-1"],
      "confidence": 0.9
    }
  ],
  "analyses": {
    "technical": {"status": "complete", "claim_ids": ["claim-1"]},
    "fundamental": {"status": "omitted", "reason": "Not applicable to scope", "claim_ids": []},
    "news": {"status": "complete", "claim_ids": []}
  },
  "analyst_report": {
    "stance": "balanced",
    "confidence": "medium",
    "headline": "One evidence-backed conclusion",
    "summary": "A concise synthesis of the independent lanes",
    "key_points": [
      {"title": "...", "assessment": "...", "claim_ids": ["claim-1"]}
    ],
    "perspectives": {
      "technical": {"impact": "mixed", "conclusion": "...", "claim_ids": ["claim-1"]},
      "fundamental": {"impact": "supportive", "conclusion": "...", "claim_ids": ["claim-1"]},
      "news": {"impact": "mixed", "conclusion": "...", "claim_ids": ["claim-1"]},
      "risk": {"impact": "cautionary", "conclusion": "...", "claim_ids": ["claim-1"]}
    },
    "monitoring_points": [
      {"signal": "...", "interpretation": "...", "claim_ids": ["claim-1"]}
    ],
    "final_assessment": {"text": "...", "claim_ids": ["claim-1"]}
  },
  "scenarios": {
    "bull": {"thesis": "...", "triggers": ["..."], "invalidation": "...", "claim_ids": ["claim-1"]},
    "base": {"thesis": "...", "triggers": ["..."], "invalidation": "...", "claim_ids": ["claim-1"]},
    "bear": {"thesis": "...", "triggers": ["..."], "invalidation": "...", "claim_ids": ["claim-1"]}
  },
  "conflicts": [],
  "review": {"verdict": "pass", "issues": [], "reviewed_at": "2026-08-14T15:30:00+09:00"},
  "limitations": ["Informational analysis only"],
  "order_action": "none"
}
```

All timestamps must use ISO 8601 with a timezone. Claim confidence is a number from 0 to 1. Use `kind: inference` for conclusions derived from evidence and explain the inference in the claim text. Schema 1.0 artifacts remain readable for compatibility, while new reports use schema 1.1 and require `analyst_report`. Analyst synthesis may only reference existing claim IDs.

## Report contract

Present:

1. Scope and as-of time
2. Senior analyst briefing with stance and confidence
3. Key points and technical, fundamental, news, and risk perspectives
4. Monitoring points that can change the assessment
5. Bull, base, and bear scenarios with triggers and invalidations
6. Conflicting evidence and uncertainties
7. Atomic claims, limitations, and source links as the evidence appendix

Avoid a single unconditional price prediction or imperative buy/sell language.
