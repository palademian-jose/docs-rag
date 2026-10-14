# Go Style Guide

Owner: Platform

## Versions and tooling

Go services use Go 1.23 and Go modules. Formatting is `gofumpt`; linting is
`golangci-lint` with the configuration in `libs/go/lint`. Both run in CI.

## When to use Go

Go is the default language for infrastructure services, CLIs and anything on
the request hot path that needs predictable latency: the API gateway, the
`order-router`, and the `edge-cache` are all Go. Product services with heavy
business logic default to Python.

## Project layout

```
cmd/<binary>/main.go     # entry points, kept thin
internal/                # private packages
pkg/                     # importable by other repositories (rare)
```

Packages are named for what they provide, not what they contain: `storage`,
not `utils`. A package named `util`, `common` or `helpers` fails review.

## Errors

Errors are values. Wrap with `fmt.Errorf("doing x: %w", err)` so callers can
use `errors.Is` and `errors.As`. Never ignore an error with `_` outside of
tests without a comment. Sentinel errors are exported as `ErrNotFound`-style
variables.

## Context

Every function that performs I/O takes `ctx context.Context` as its first
parameter. Contexts are never stored in structs. Request handlers derive a
context with a timeout no longer than the route's SLO.

## Concurrency

Goroutines are started only with a clear owner that waits for them, typically
`errgroup.Group`. Channels are documented with their direction and closing
rules. Shared state is protected with `sync.Mutex`; `sync/atomic` is used only
for counters.

## Testing

Tests use the standard library `testing` package with table-driven tests and
`testify/require` for assertions. Integration tests run with the `integration`
build tag and are executed in CI against containers started by
`testcontainers-go`.

## Observability

Services expose Prometheus metrics on `/metrics` and use OpenTelemetry for
traces. The `larkspur-go/telemetry` package sets up both with one call in
`main`.
