# Messaging and Events

Owner: Data Platform

## Platform

Asynchronous communication between services uses Kafka. There is one cluster
per production region with six brokers and a replication factor of three.
Topics are created through the `kafka-topic` Terraform module; ad-hoc topic
creation is disabled.

## Topic naming

Topics are named `<domain>.<entity>.<event>` in the past tense, for example
`orders.order.created` or `payments.refund.settled`. Topics are owned by the
service that produces to them and have exactly one producer service.

## Schemas

Every message is a protobuf payload registered in the schema registry. Schema
changes must be backward compatible: fields are never removed or renumbered,
only deprecated. The `schema-check` CI job rejects incompatible changes.

## Message envelope

Every event carries the standard envelope: `event_id` (UUID), `event_type`,
`occurred_at` (RFC 3339), `producer`, `trace_id` and `payload`. The
`event_id` is used by consumers for deduplication.

## Delivery guarantees

Delivery is at-least-once. Consumers MUST be idempotent: they record processed
`event_id` values in their own datastore with a 7-day retention and skip
duplicates. Exactly-once semantics are not provided and should not be
assumed.

## Retention and partitions

Default topic retention is 7 days. Topics that feed analytics have 30-day
retention. Partition counts start at 12 and are increased only through a
Data Platform review because repartitioning changes key ordering.

## Consumer groups

Consumer group names are `<service>.<purpose>`. A consumer that falls more
than 100,000 messages behind triggers a lag alert to the owning team; lag
over one million messages pages.

## Dead letters

Messages that fail processing three times are moved to
`<topic>.deadletter` with the error attached as a header. Dead-letter topics
have 14-day retention. Teams review their dead letters weekly; a growing
dead-letter topic is treated as a bug, not as noise.

## Outbox pattern

Services that must write to their database and publish an event atomically
use the transactional outbox: the event is written to an `outbox` table in
the same transaction and a relay process publishes it to Kafka. The
`larkspur-outbox` library provides the relay.
