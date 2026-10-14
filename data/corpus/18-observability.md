# Observability

Owner: Site Reliability Engineering (SRE)

## The three signals

Every service emits structured logs, Prometheus metrics and OpenTelemetry
traces. The `larkspur-telemetry` library for each language configures all
three with a single initialisation call and injects the `trace_id` into logs.

## Logging

Logs are JSON lines written to stdout and shipped by the cluster's Vector
agent to Loki. Required fields are `timestamp`, `level`, `service`,
`trace_id` and `message`. Log levels are `DEBUG`, `INFO`, `WARN` and `ERROR`;
production runs at `INFO`. Logging request bodies or any personal data is
forbidden; the `log-scrubber` filter redacts known patterns (emails, card
numbers, bearer tokens) as a safety net, not as a substitute for care.

Log retention is 30 days in Loki, with `ERROR` lines additionally archived to
object storage for one year.

## Metrics

Metrics follow Prometheus naming: `larkspur_<service>_<name>_<unit>`, for
example `larkspur_order_router_requests_total`. Every HTTP and gRPC service
exposes the RED metrics (rate, errors, duration) automatically through the
telemetry middleware. Histograms use the shared bucket set
`[5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s]`.

Cardinality is the main risk: labels MUST NOT include user ids, order ids or
other unbounded values. The metrics pipeline drops any series whose label set
exceeds 10,000 distinct combinations and posts a warning.

## Tracing

Traces are sampled at 10% in production and 100% in `dev` and `staging`,
with tail-based sampling that always keeps traces containing an error or a
span over two seconds. Traces are stored in Tempo for 14 days. Every
outbound call (HTTP, gRPC, database, queue) creates a child span.

## Dashboards and alerts

Dashboards are defined as code in `infra/grafana/` using Jsonnet and deployed
with the service. Hand-edited dashboards in the Grafana UI are overwritten on
the next deploy. Alerts are defined in `alerts.yaml` in the service directory
and follow the burn-rate pattern from the SLO page.

## Cost of observability

Observability spend is budgeted at 8% of the infrastructure bill. Teams that
exceed their share receive a weekly report listing the highest-volume log
lines and highest-cardinality metrics.
