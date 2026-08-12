# ClickHouse Admin Dashboard Spec

## Overview

Single Grafana dashboard for ClickHouse cluster administrators.
**Primary use case:** on-call incident response.
**Default time range:** last 6 hours (quick-select: 1h, 24h, 7d).
**Data sources:** ClickHouse Prometheus exporter (time-series) + grafana-clickhouse-datasource (SQL snapshots).

---

## Dashboard Variables

| Variable        | Description                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `$datasource`   | Prometheus datasource                                                       |
| `$cluster`      | ClickHouse cluster label as scraped by Prometheus. Note: does not currently match the internal ClickHouse cluster name in `remote_servers` — SQL panels using `clusterAllReplicas('$cluster', ...)` will align once the names are unified. |
| `$ch_datasource` | grafana-clickhouse-datasource instance (no regex filtering)                |
| `$pod`          | Filter by pod name (multi-select, defaults to all)                          |

Shard variable removed — shard-level granularity is not used.

---

## Section 1 — General Health

> First panel is an error table for immediate at-a-glance triage.

| Panel | Description |
|-------|-------------|
| Active Errors | `system.errors` across all nodes — error name, last message, count, last seen. Sorted by most recent. |
| CPU Usage — per Pod | Normalised CPU %: `(OSUserTime + OSSystemTime) / OSNumVirtualCPUs`. Shows 0–100% regardless of core count. |
| RAM Usage — per Pod | `MemoryTracking` bytes per pod |
| Network I/O — per Pod | RX + TX bytes/sec per pod |
| Storage Used (Hot) — per Pod | Hot-tier disk bytes per pod. Cross-replica divergence indicates merge lag or TTL running unevenly. |
| Failed Queries/sec — per Pod | Rate of failed queries. A spike on one pod points to a bad replica. |

---

## Section 2 — Inserts

| Panel | Description |
|-------|-------------|
| Insert Throughput — per Table | Rows/sec per table from `system.query_log` |
| Insert Throughput — per Replica (Pod) | Rows/sec per pod from Prometheus |
| Active Parts — per Table (snapshot) | Current part count per table from `system.parts` |
| Async Insert — Pending Queue Depth | Server-side async insert buffer depth. Growing queue = data loss risk on restart. |
| INSERT Queries per Second | INSERT QPS per pod |
| Average INSERT Latency — per Pod | Mean INSERT duration in ms |
| Async Insert — Batch Size (Rows per Flush) | `AsyncInsertRows / AsyncInsertsFlushed`. Low values mean clients send tiny inserts and batching is ineffective. |

---

## Section 3 — Queries

> SELECT-only metrics. INSERT metrics live in the Inserts section.

| Panel | Description |
|-------|-------------|
| Query Latency (avg) — per Pod | Average duration across all query kinds |
| Queries per Second (Total) | Total QPS per pod (all kinds) |
| SELECT Queries per Second | SELECT QPS per pod |
| Average SELECT Latency — per Pod | Mean SELECT duration in ms |

---

## Section 4 — Merges

| Panel | Description |
|-------|-------------|
| Active Background Merges — per Pod | `BackgroundMergesAndMutationsPoolTask` per pod |
| Merge Pool Saturation | Active merges vs pool size + saturation % on right axis. Saturation at 100% while part count rises = merges cannot keep pace. |
| Async Insert Buffered Flushes/sec | Flush rate to disk. High rate = many small batches. |

**Note:** ClickHouse has no explicit merge queue depth metric. Backlog is inferred from saturation + rising part count.

---

## Section 5 — Replication & Keeper

| Panel | Description |
|-------|-------------|
| Replication Queue Depth — per Replica | Pending tasks per replica from `system.replication_queue` |
| Replication Lag — per Replica | Age of oldest pending task per replica (seconds) |
| Keeper Liveness — per Pod | ALIVE/DEAD based on active ZooKeeper sessions. Loss of Keeper stops all replication and DDL. |

---

## Section 6 — S3

| Panel | Description |
|-------|-------------|
| S3 Storage Used | Total bytes in S3 tier per pod |
| S3 Write Throughput | Bytes/sec written to S3 |
| S3 Read Throughput | Bytes/sec read from S3 |
| S3 GET Operations/sec | GET request rate per pod |
| S3 Merge Reads (bytes/sec) | Bytes read from S3 by background merges |
| S3 GET Attribution — by Source | SQL table breaking down S3 GETs by source: User SELECT, INSERT, Merge/OPTIMIZE, TTL, Other. Useful for diagnosing unexpected GET spikes. |

---

## Section 7 — I/O

| Panel | Description |
|-------|-------------|
| Open File Operations/sec | File open syscalls per second per pod |
| Read Compressed Bytes/sec | Compressed bytes read from disk per second |
| Read Compressed Blocks/sec | Compressed blocks read per second |
| Failed Replicated Part Fetches/sec | Failed replica fetch attempts. Sustained failures = broken replica or network issue. |
| Network RX Imbalance Ratio | `max(RX) / min(RX)` across pods. >2 = yellow, >5 = red. Signals load balancer misconfiguration or distributed query coordinator hot-spotting. |

---

## Section 8 — Parts

| Panel | Description |
|-------|-------------|
| Total Active Parts — per Pod | Total MergeTree parts. Rising trend = merges not keeping pace. |
| Parts per Table — Top 20 | Current part count per table |
| Parts per Partition — Top 20 | Partitions with the most active parts |
| Largest Parts by Size — Top 20 | Individual parts sorted by disk size |
| Detached Parts — per Node | Detached parts from `system.detached_parts`. Any non-zero value requires investigation. |
| Total Parts vs SELECT Latency | Dual Y-axis: part count (left) + SELECT latency (right). Shows query performance correlation with merge lag. |
| Mark Cache Hit Rate — per Pod | `MarkCacheHits / (Hits + Misses)`. Falling hit rate alongside rising parts = merge lag degrading reads. |
| Too Many Parts — Current Error State | `system.errors WHERE name = 'TOO_MANY_PARTS'` across all nodes. Non-zero = ClickHouse is throttling inserts. |
| Oldest Active Part per Table | Age (hours) of oldest part per table. Very old parts in busy tables indicate stalled merges. |

---

## Metric Sources

| Source | Used for |
|--------|----------|
| ClickHouse Prometheus exporter (`/metrics`) | Time-series panels: throughput, latency, queue depths, pool saturation, cache hit rates |
| grafana-clickhouse-datasource (SQL on `system.*`) | Snapshot tables: parts, replication queue, errors, S3 attribution |

---

## Open Questions

- [ ] Confirm `BackgroundMergesAndMutationsPoolSize` is exposed by the exporter in use
- [ ] Confirm Keeper metrics are exposed (some exporters require explicit config)
- [ ] Define S3 alert thresholds (what GET rate or storage % triggers a page?)
- [ ] Align `$cluster` Prometheus label with ClickHouse internal cluster name in `remote_servers` so SQL panels work correctly
- [ ] Watermark service monitoring — deferred, add as a separate section when the service exposes its Prometheus endpoint
