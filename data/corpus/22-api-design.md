# API Design Guidelines

Owner: Architecture Review Board

## Public versus internal APIs

Public APIs are consumed by customers and partners and are versioned in the
URL path: `/v1/orders`, `/v2/orders`. Internal APIs between services use
gRPC with protobuf and are versioned through the package name
(`larkspur.orders.v1`). REST is used for public APIs because customers ask
for it; gRPC is used internally for its typed contracts.

## Versioning policy

A public API version is supported for at least 18 months after its successor
is released. Deprecation is announced in the changelog, in the `Deprecation`
and `Sunset` response headers, and by email to affected API key owners 90
days before the sunset date. Breaking changes always require a new major
version; additive changes (new optional fields, new endpoints) do not.

## Resource naming

- Plural nouns, lowercase, hyphenated: `/v1/payment-methods`.
- Nested resources at most two levels deep: `/v1/orders/{id}/items`.
- Actions that do not map to CRUD use a verb suffix: `/v1/orders/{id}:cancel`.
- Identifiers are opaque strings with a type prefix: `ord_8f3k2m`,
  `cus_19xd0q`. Sequential integer ids are never exposed.

## Requests and responses

Bodies are JSON with `snake_case` field names. Timestamps are RFC 3339 in
UTC. Money is represented as an integer amount in minor units plus an ISO
4217 currency code, never as a float. Lists are paginated with cursor
pagination: `?limit=50&cursor=...`, returning `next_cursor` or `null`.

## Errors

Errors use the RFC 9457 problem details format with `type`, `title`,
`status`, `detail` and a `request_id`. The `type` is a stable URL such as
`https://api.larkspur.com/errors/insufficient-funds`. Validation errors
include an `errors` array with `field` and `message` for each problem.

## Idempotency

All `POST` endpoints that create resources accept an `Idempotency-Key`
header. Keys are stored for 24 hours; a repeated request with the same key
and body returns the original response, and a repeated key with a different
body returns HTTP 422.

## Rate limiting

Public APIs apply a per-key token bucket of 600 requests per minute with a
burst of 100. Responses include `RateLimit-Limit`, `RateLimit-Remaining` and
`RateLimit-Reset` headers, and a 429 response includes `Retry-After`.

## Review process

New public endpoints and any breaking change go through an API review: the
OpenAPI diff is posted to `#api-review` and two members of the Architecture
Review Board approve. The `openapi-lint` check enforces naming, pagination
and error-format rules automatically.
