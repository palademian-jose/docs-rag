# Testing Strategy

Owner: Developer Experience (DevEx)

## The test pyramid

We aim for roughly 70% unit tests, 20% integration tests and 10% end-to-end
tests by count. Unit tests run on every commit, integration tests run on every
pull request, and end-to-end tests run on merge to `main` and nightly against
staging.

## Unit tests

Unit tests exercise one module in isolation and run without network, disk or
clock dependencies. A unit test suite for a service MUST finish in under 60
seconds on a laptop. Tests that need the clock use the injected `Clock`
interface; tests that need randomness seed it explicitly.

## Integration tests

Integration tests run the service against real dependencies started in
containers: Postgres, Redis, Kafka and any internal service stubs. They are
tagged `integration` and executed with `lark test --integration`. Each test
creates its own schema or key prefix so tests can run in parallel.

## End-to-end tests

End-to-end tests drive the product through its public surface (browser or
API) against the `staging` environment. They live in the `e2e` directory of
the monorepo and use Playwright for web and `k6` for API flows. The suite is
owned by the Quality Engineering guild and must complete in under 20 minutes.

## Contract tests

Services that publish events or expose APIs consumed by other teams maintain
Pact contract tests. A provider build fails if it breaks a contract published
by any consumer in the Pact Broker.

## Flaky tests

A test that fails without a code change is flaky. The `flake-hunter` bot
quarantines a test after three unexplained failures in seven days by moving
it to the `quarantine` group, which still runs but does not block merges. The
owning team has ten working days to fix or delete a quarantined test.

## Coverage

Coverage is measured but not gated: there is no minimum percentage. Pull
requests that decrease coverage by more than two percentage points receive a
comment from the `coverage` bot and the reviewer decides whether it matters.

## Test data

Never use production data in tests. Fixture factories live in each service's
`tests/factories` directory; the `faker` library generates realistic values.
Personally identifiable information in fixtures must be obviously synthetic,
for example addresses in the `example.com` domain.

## Performance tests

Tier-1 services run a load test with `k6` before every release train. The test
replays a recorded production traffic profile at 1.5x volume against staging
and fails if p95 latency regresses by more than 10% against the previous
release.
