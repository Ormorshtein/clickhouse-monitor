# Local Test Environment

Spins up a minimal ClickHouse cluster + Prometheus + Grafana for dashboard testing.

## Stack

| Container | Role | Ports |
|---|---|---|
| `ch-keeper-0` | ClickHouse Keeper (ZK-compatible) | 9181 (keeper), 9363 (metrics) |
| `ch-clickhouse-0` | ClickHouse replica 1 | 8123 (HTTP), 9000 (TCP), 9363 (metrics) |
| `ch-clickhouse-1` | ClickHouse replica 2 | 8124 (HTTP), 9001 (TCP) |
| `prometheus` | Prometheus | 9090 |
| `grafana` | Grafana | 3000 |

## Start

```bash
cd local
docker compose up -d
```

Grafana takes ~30s to install the ClickHouse plugin on first start.

## Insert test data

```bash
python3 scripts/seed_data.py
```

## Open dashboard

1. Go to http://localhost:3000
2. Navigate to Dashboards → clickhouse-admin
3. Set variables:
   - **Prometheus**: select `Prometheus`
   - **Cluster**: select `default`
   - **ClickHouse SQL**: select `ClickHouse`
   - **Pod**: `All`

## Stop

```bash
docker compose down          # keep data
docker compose down -v       # also delete volumes
```
