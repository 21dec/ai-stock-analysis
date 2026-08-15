# Risk and approval policy

## Frozen anchors

- Source records and timestamps remain attached to the claims they support.
- Evaluation fixtures remain unchanged during the run being evaluated.
- The deterministic validator must pass without weakening its rules.
- `order_action` remains `none` for this skill.
- A human decides whether any output is published or used for a transaction.

## Approval gates

Obtain a separate, explicit approval immediately before:

- posting or publishing a report externally;
- sending a message to another person or service;
- deploying a report or workflow;
- creating, modifying, or transmitting an order;
- accessing a production account or private financial data.

Show the exact target and payload before requesting approval. Analysis approval does not imply execution approval.

## Stop conditions

Stop and report the gap when:

- a current price or material news item cannot be verified;
- authoritative sources conflict and the conflict cannot be resolved;
- requested access exceeds the current permission scope;
- validation still fails after two corrections;
- the request would turn informational analysis into personalized or autonomous trading.
