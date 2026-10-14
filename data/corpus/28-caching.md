# Caching

Owner: Platform

## Layers

Larkspur caches at three layers, each with a different owner:

1. **Edge cache** - the CDN caches public, unauthenticated responses with
   `Cache-Control` headers set by the service. Owned by Web Platform.
2. **Application cache** - Redis clusters, one per team, used for sessions,
   rate-limit counters and computed results. Owned by the service team.
3. **In-process cache** - small LRU caches inside a service for configuration
   and reference data. Owned by the service team.

## Redis

Each team has a Redis cluster in each production region, provisioned with the
`redis-cluster` Terraform module. Clusters run Redis 7 with three shards and
one replica per shard. Keys are prefixed with the service name
(`order-router:session:<id>`) and every key MUST have a TTL; the
`redis-audit` job lists keys without a TTL weekly and the owning team must
fix them.

The default TTLs are 15 minutes for computed results and 24 hours for
sessions. Values larger than 512 KB are rejected by the client library.

## Cache-aside pattern

Services use cache-aside: read from the cache, on a miss read from the
database and populate the cache. Write-through is used only for session
data. Services MUST function, albeit more slowly, when Redis is unavailable;
the client library returns a miss on connection errors and emits the
`cache_unavailable` metric.

## Stampede protection

Hot keys use a probabilistic early-expiry window and a per-key lock so that
only one request recomputes an expired value. The `larkspur-cache` library
implements this with `get_or_compute(key, ttl, fn)`.

## Invalidation

Caches are invalidated by publishing an event on the `cache.invalidate`
Kafka topic with the key pattern. Services subscribe and delete matching
keys. Time-based expiry remains the safety net; never rely on invalidation
alone for correctness-critical data.

## What not to cache

Do not cache anything containing payment card data, credentials or personal
data classified as Restricted. Do not cache responses to authenticated
requests at the edge. Do not cache negative results (not-found) for longer
than 30 seconds.

## Monitoring

The cache dashboard shows hit rate, p99 latency and memory usage per cluster.
A hit rate below 80% for a cache intended as a read-through is a signal that
the TTL or key design needs review.
