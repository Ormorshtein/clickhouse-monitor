#!/usr/bin/env python3
"""
Seed data into the local ClickHouse cluster for dashboard testing.
Creates a replicated table and continuously inserts + queries data.

Usage:
    python3 seed_data.py
"""

import time
import random
import urllib.request
import urllib.parse

CH_HOST = "http://localhost:8123"


def query(sql: str, host: str = CH_HOST) -> str:
    data = sql.encode()
    req = urllib.request.Request(host, data=data)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode()


def setup():
    print("Creating database and replicated table...")
    query("CREATE DATABASE IF NOT EXISTS metrics ON CLUSTER default")

    query("""
        CREATE TABLE IF NOT EXISTS metrics.events ON CLUSTER default
        (
            ts       DateTime DEFAULT now(),
            service  LowCardinality(String),
            event    LowCardinality(String),
            value    Float64,
            user_id  UInt32
        )
        ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/metrics/events', '{replica}')
        PARTITION BY toYYYYMM(ts)
        ORDER BY (service, ts)
    """)

    query("""
        CREATE TABLE IF NOT EXISTS metrics.events_dist ON CLUSTER default
        AS metrics.events
        ENGINE = Distributed(default, metrics, events, rand())
    """)

    query("""
        CREATE TABLE IF NOT EXISTS metrics.traces ON CLUSTER default
        (
            ts          DateTime DEFAULT now(),
            trace_id    String,
            span_name   LowCardinality(String),
            duration_ms Float64,
            status      LowCardinality(String)
        )
        ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/metrics/traces', '{replica}')
        PARTITION BY toYYYYMM(ts)
        ORDER BY (span_name, ts)
    """)

    query("""
        CREATE TABLE IF NOT EXISTS metrics.traces_dist ON CLUSTER default
        AS metrics.traces
        ENGINE = Distributed(default, metrics, traces, rand())
    """)
    print("Tables ready.")


def insert_batch(batch_size: int = 500):
    services = ["api", "worker", "scheduler", "gateway", "auth"]
    events   = ["request", "error", "timeout", "retry", "success"]
    rows = []
    for _ in range(batch_size):
        rows.append(
            f"(now(), '{random.choice(services)}', '{random.choice(events)}', "
            f"{random.uniform(0, 100):.4f}, {random.randint(1, 100000)})"
        )
    sql = f"INSERT INTO metrics.events_dist (ts, service, event, value, user_id) VALUES {','.join(rows)} SETTINGS async_insert=1, wait_for_async_insert=0"
    query(sql)

    spans    = ["http.request", "db.query", "cache.get", "rpc.call", "queue.publish"]
    statuses = ["ok", "ok", "ok", "error", "timeout"]
    trace_rows = []
    for _ in range(batch_size // 3):
        trace_id = f"{random.randint(0, 0xFFFFFFFF):08x}{random.randint(0, 0xFFFFFFFF):08x}"
        trace_rows.append(
            f"(now(), '{trace_id}', '{random.choice(spans)}', "
            f"{random.uniform(1, 500):.2f}, '{random.choice(statuses)}')"
        )
    sql = f"INSERT INTO metrics.traces_dist (ts, trace_id, span_name, duration_ms, status) VALUES {','.join(trace_rows)} SETTINGS async_insert=1, wait_for_async_insert=0"
    query(sql)


def run_selects():
    queries = [
        "SELECT service, count() FROM metrics.events GROUP BY service",
        "SELECT event, avg(value) FROM metrics.events GROUP BY event",
        "SELECT count() FROM metrics.events WHERE ts > now() - INTERVAL 1 HOUR",
        "SELECT service, event, sum(value) FROM metrics.events GROUP BY service, event ORDER BY sum(value) DESC LIMIT 10",
    ]
    for sql in random.sample(queries, k=2):
        try:
            query(sql)
        except Exception:
            pass


def main():
    print("Waiting for ClickHouse to be ready...")
    for _ in range(30):
        try:
            query("SELECT 1")
            break
        except Exception:
            time.sleep(2)
    else:
        print("ClickHouse not reachable after 60s — is the cluster running?")
        return

    setup()

    print("Inserting data continuously. Press Ctrl+C to stop.")
    batch = 0
    while True:
        try:
            insert_batch(random.randint(200, 800))
            batch += 1
            if batch % 5 == 0:
                run_selects()
            print(f"Batch {batch} inserted", end="\r")
            time.sleep(random.uniform(0.5, 2.0))
        except KeyboardInterrupt:
            print(f"\nStopped after {batch} batches.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
