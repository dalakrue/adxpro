# Finnhub valid-key connection correction — 2026-06-17

## Root cause
The previous connector validated every token with the forex quote endpoint for
`OANDA:EUR_USD`. A valid token can receive a plan/endpoint access response there,
and the old code treated every HTTP 401/403 as an invalid key. This produced the
misleading message shown in the UI.

## Corrections
- Validate first with the actual NLP market-news endpoint.
- Fall back from forex news to general news, then to US symbol metadata for an
  authentication-only check.
- Distinguish invalid authentication, plan restriction, rate limiting, service
  failure, and malformed key.
- Normalize copied token values, quoted values, `token=...` text, full Finnhub
  URLs, line breaks, and invisible Unicode characters.
- Allow **Test** immediately after a token is typed, even before Connect.
- A successful Test also connects the session.
- Preserve an already-working session key when a replacement key fails.
- Use general-news fallback for NLP if forex news is restricted.
- Enable redirects and add explicit JSON/User-Agent headers.
- Keep the key session-only and redact it from every displayed error.
