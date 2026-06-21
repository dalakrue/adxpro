# Copy and Export Specification

## Canonical service

All visible copy locations call `services.canonical_exports`. Menu, Lunch Field 1, and Field 6 use the same generation-bound service.

## Copy Short

Hard limits: 40 lines, 6,000 characters, and a target ceiling of about 1,500 estimated tokens. The builder removes optional low-priority lines first, shortens verbose reasons/warnings, removes duplicate wording, and never character-truncates a numeric value. If compression occurs, it appends `[Short export compressed to configured limit]`.

Required content: symbol/timeframe, completed candle, current price, current and less-risky decisions, priority/rank, regime/reliability, five protected scores, forecast direction/horizon, interval, uncertainty/error, freshness, up to three reasons, up to three blockers/warnings, and generation identity. Prepared payload UI shows character, line, and token estimates.

## Copy All

Generated only on press and cached by generation identity. It contains structured summaries of all six fields, relevant history summaries, evidence, and limitations. It deliberately excludes every raw history row and the raw canonical/database payload.

## JSON

The complete machine-readable JSON remains a separate explicit action and is generated only on demand. It contains the canonical generation, compact display summary, and risk plan.

## Parity

Tests verify that Menu and Lunch use the same service for a given generation, Copy Short remains bounded, and Copy All names all six fields.
