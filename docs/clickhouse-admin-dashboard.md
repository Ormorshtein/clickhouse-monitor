# ClickHouse Admin Dashboard Spec

## Overview

Single Grafana dashboard for ClickHouse cluster administrators.
**Primary use case:** on-call incident response.
**Default time range:** last 6 hours (quick-select: 1h, 24h, 7d).
**Data source:** ClickHouse Prometheus exporter, one ServiceMonitor per cluster, metrics labeled by pod name (StatefulSet — pod names are stable).

---

## Dashboard Variables

| Variable   | Description                                                    |
|------------|----------------------------------------------------------------|
| `$cluster` | Selects which ClickHouse cluster (one data source per cluster) |
| `$pod`     | Filter by pod name (e.g. `clickhouse-0`, `clickhouse-1`)       |
| `$table`   | Filter by table name for insert/parts panels                   |

---

## Section 1 — General Health (Summary Row)

> Small summary row. Links to the Infra Admin dashboard for full detail.
> Each metric has two panels: one per pod, one aggregated per shard.

| Panel | Granularity | Description |
|-------|-------------|-------------|
| CPU usage | Per pod + per shard | CPU % per pod; aggregated per shard |
| RAM usage | Per pod + per shard | Memory bytes used per pod; aggregated per shard |
| Network I/O | Per pod + per shard | Inbound + outbound bytes/sec |
| Storage used | Per pod + per shard | Disk bytes used on PowerFlex volume |

8 panels total in this row (4 metrics × 2 granularities).

---

## Section 2 — Inserts

| Panel | Description |
|-------|-------------|
| Insert throughput — per table | Rows/sec grouped by `$table` |
| Insert throughput — per shard | Rows/sec aggregated per shard |
| Insert throughput — per replica (pod) | Rows/sec per pod name |
| Part count per table | Active part count grouped by table; use `$table` to narrow to partition-level breakdown |
| Async insert queue depth | Pending async insert buffer size — early warning for data loss risk |

**Note on part count per partition:** Partition-level granularity is available via `system.parts` but can produce hundreds of series. Default view is per-table; filter with `$table` to expose per-partition detail.

---

## Section 3 — Queries

| Panel | Description |
|-------|-------------|
| Query latency — per pod | p50 / p95 / p99 query duration per pod |
| Queries per second (total) | Overall QPS across the cluster |
| SELECT queries per second | QPS for read queries only |
| INSERT queries per second | QPS for write queries only |
| Average latency — SELECT | Mean SELECT duration |
| Average latency — INSERT | Mean INSERT duration |

---

## Section 4 — Merges

| Panel | Description |
|-------|-------------|
| Active merges | Currently running merges (`BackgroundMergesAndMutationsPoolTask`) per pod |
| Merge pool saturation | Active merges overlaid against pool size (`BackgroundMergesAndMutationsPoolSize`) — saturation means pool is full while part count grows |
| Buffered flushes | Async insert buffer flushes per second |

**Active vs queued:** ClickHouse has no explicit "merge queue depth" metric. Merge backlog is inferred from the saturation panel: when active merges equal pool size and part count is rising, merges cannot keep pace with inserts.

---

## Section 5 — Replication & Keeper

> Minimal panels — Keeper issues are critical but rare.

| Panel | Description |
|-------|-------------|
| Replication queue depth | Pending replication tasks per pod (`system.replication_queue` count) |
| Replication lag | Age of oldest pending replication task per pod |
| Keeper connections | Number of active Keeper connections per pod |

---

## Section 6 — Backup & Restore (S3)

| Panel | Description |
|-------|-------------|
| S3 storage used | Total bytes stored in S3 (tiered storage) |
| S3 write throughput | Bytes/sec written to S3 |
| S3 read throughput | Bytes/sec read back from S3 |
| S3 GET operations/sec | GET request rate — cost and latency indicator |
| S3 merge reads | Read operations triggered by background merges on tiered data |

---

## Section 7 — I/O

| Panel | Description |
|-------|-------------|
| Open file operations/sec | File open syscalls per second per pod |
| Read compressed bytes/sec | Compressed bytes read from disk per second |
| Read blocks/sec | Disk blocks read per second |
| Failed part fetches | Failed replication fetch attempts per replicated part — indicates replica sync issues |

---

## Section 8 — Parts

> Minimal panels — detail available via `system.parts` queries.

| Panel | Description |
|-------|-------------|
| Total active parts | Count of active parts across all tables |
| Parts per table (top N) | Bar chart — tables with the most parts |
| Parts created vs merged per second | Rate of part creation vs merge completion — shows whether merges are keeping pace with inserts |

---

## Section 9 — Errors

| Panel | Description |
|-------|-------------|
| Top errors by type | `system.errors` — error name, count, last occurrence |
| Error rate per pod | Total errors/sec per pod — useful for spotting a single bad replica |

---

## Metric Sources

| Source | Used for |
|--------|----------|
| ClickHouse Prometheus exporter (`/metrics`) | Time-series panels: throughput, latency, queue depths, pool saturation |
| ClickHouse data source (SQL on `system.*`) | Snapshot panels: part counts, replication queue contents, error table |

---

## Open Questions

- [ ] Confirm `BackgroundMergesAndMutationsPoolSize` is exposed by the exporter in use
- [ ] Confirm Keeper metrics are exposed (some exporters require explicit config)
- [ ] Define S3 alert thresholds (what GET rate or storage % triggers a page?)
- [ ] Watermark service monitoring — deferred, add as a separate section when the service exposes its Prometheus endpoint
