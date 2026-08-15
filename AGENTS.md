# Stock Analysis Project

## Safety anchors

- Treat every analysis as informational research, not personalized financial advice.
- Never place, simulate as real, or transmit a securities order without a separate explicit user request and confirmation of the exact order.
- Record a source URL and an as-of timestamp for every time-sensitive price, indicator, filing, and news claim.
- Label estimates and inferences; do not present them as verified facts.
- Keep bull, base, and bear scenarios, including an invalidation condition for each.
- Do not weaken validation rules or edit evaluation fixtures merely to make a failing run pass.
- Stop and report the gap when current or authoritative evidence cannot be obtained.

## Workflow governance

- Use `.agents/skills/run-stock-analysis-graph` for evidence-backed stock analysis requests.
- Delegate only independent, bounded research or review lanes to subagents.
- Keep concurrent write work single-owner; use subagents primarily for read-heavy research and review.
- Separate the primary analysis from the adversarial review when the task is material.
- Require the deterministic evidence validator to pass before presenting a result as validated.
- Require explicit user approval before external publication, messaging, deployment, or any transaction-related action.

## Project checks

- Run `python3 -m unittest discover -s tests` after changing Python behavior.
- Write Git commit messages in Korean.
