# YugabyteDB Benchmark & Testing Tools

A modern Python testing suite and CLI tool for benchmarking YugabyteDB read/write performance and validating distributed SQL features (like Hash vs. Range sharding) using a local multi-node Docker Compose cluster.

## Architecture

- **3-Node `yugabyted` Cluster**: Runs `yb-node1`, `yb-node2`, and `yb-node3` via Docker Compose using the official LTS image (`yugabytedb/yugabyte:2024.2.8.0-b85`).
- **Storage**: Ephemeral Docker volumes for each node, capped by Docker deploy limits (2GiB per node).
- **Tooling**: Built with Python 3.11+, using `uv` for dependency management and `psycopg2-yugabytedb-binary` as the Smart Driver.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package and project manager)

## Quick Start

### 1. Setup Environment
Clone the repository and install dependencies using `uv`:
```bash
uv sync --extra dev
```

### 2. Start the Cluster
Spin up the 3-node YugabyteDB cluster. The Makefile target handles waiting for the cluster to elect leaders and become fully ready (~45 seconds).
```bash
make cluster-up
```

### 3. Run Benchmarks & Tests

**A. Multi-Node Sharding Test (Hash vs. Range)**
Validates cluster health, schema initialization, and compares the range-query latency between Hash-sharded and Range-sharded tables.
```bash
make test-multi-node
```

**B. Read/Write Throughput Benchmarks**
Run the end-to-end data generation, parallel COPY write benchmarks, and standard vs optimized read benchmarks.
*(Make sure the cluster is running first!)*
```bash
make all-tests
```

### 4. Teardown
When finished, stop the cluster and wipe all ephemeral data volumes to ensure a clean state for next time:
```bash
make cluster-down
```

---

## Detailed Benchmark Modes

All Read/Write benchmarking modes report detailed metrics including: **QPS, TPS, IOPS, and Latency (avg/p95/p99)**. You can run individual benchmark steps directly via `uv run` and `src/main.py`.

### Write Benchmarks

```bash
# Standard single-thread COPY (Generates mock data and inserts 1,000,000 rows)
uv run python src/main.py --mode single --file data.csv --generate 1000000

# Parallel COPY with Smart Driver (20 concurrent workers, reuse existing data.csv)
uv run python src/main.py --mode parallel --file data.csv --workers 20 --no-init
```

### Read Benchmarks

```bash
# Standard range queries (against an unoptimized table)
uv run python src/main.py --mode read_standard --file data.csv --no-init --workers 10 --duration 60

# Optimized range queries (against a table with a specialized Covering Index)
uv run python src/main.py --mode read_optimized --file data.csv --no-init --workers 10 --duration 60
```

## CLI Reference (`src/main.py`)

| Argument       | Default    | Description                                           |
|----------------|------------|-------------------------------------------------------|
| `--mode`       | (required) | `single`, `parallel`, `read_standard`, `read_optimized` |
| `--file`       | (required) | Path to CSV file for data reading/writing             |
| `--generate`   | —          | Generate N rows into `--file` before benchmark          |
| `--workers`    | 10         | Concurrent threads used during parallel read/writes     |
| `--chunk-size` | 10000      | Rows per chunk (used in parallel write mode)          |
| `--duration`   | 60         | Seconds to run the read benchmark                     |
| `--no-init`    | false      | Skip schema drop/recreate; only truncate tables       |

## Advanced: Index Strategy

For the Read Benchmark (`read_standard` vs `read_optimized`), the following indexing strategies are compared:

| Mode | Table | Index |
|---|---|---|
| `read_standard` | `test_data` | Primary Key (`id ASC`) only |
| `read_optimized` | `test_data_optimized` | Covering: `score DESC, name ASC INCLUDE (email, created_at)` |

*The optimized index avoids expensive double-lookups out to the main table heap and completely eliminates in-memory sorts by physically matching the query's `ORDER BY score DESC, name ASC` clause constraint, while covering all projected columns.*

---

## Kubernetes Write Path Tracing & Verification (Current Branch `yb-inspector` Features)

This branch introduces an automated tool to trace a write query (`INSERT`) from the YSQL engine down through DocDB, the Raft consensus group, and finally to the MemTable. It runs inside a Kubernetes cluster, collects distributed replica logs, filters them by a unique trace ID, and verifies that the write path matches expected execution stages.

### Core Components

*   **Tracer Client & Collector** ([trace_db.py](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/src/trace_db.py), [trace_k8s.py](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/src/trace_k8s.py), [trace_main.py](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/src/trace_main.py)): Connects to YSQL, generates and inserts a row with a unique `trace_id`, concurrently streams and filters container stdout logs from multiple `yb-tserver` pods using `kubernetes` Python SDK, and appends them with standard UTC timestamps to a shared volume.
*   **Trace Verifier** ([src/trace_verifier/](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/src/trace_verifier/)): Command-line analyzer that parses a set of write path rules ([trace_rules.yaml](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/trace_rules.yaml)) and verifies whether the expected log patterns (e.g., YSQL parse, Raft WAL append, consensus update, MemTable apply) are present in the trace logs.
*   **Kubernetes Resources** ([k8s/job.yaml](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/k8s/job.yaml), [k8s/rbac.yaml](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/k8s/rbac.yaml), [Dockerfile.tracer](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/Dockerfile.tracer)): ServiceAccount with read-only access to pod logs, and a Job configuration executing the trace workflow with a PVC mount to persist log reports.

### Usage

#### 1. Setup Prerequisites
Ensure you are connected to a Kubernetes cluster running YugabyteDB in the `yb-demo` namespace (with pods named `yb-tserver-0`, `yb-tserver-1`, `yb-tserver-2`). Build and load the Docker image `custom/yb-tracer:latest`, and apply RBAC configuration:
```bash
kubectl apply -f k8s/rbac.yaml
```

#### 2. Execute Trace and Verification
Run the following make command to delete any existing trace job, trigger a new tracer execution, retrieve the logs, and verify the write path steps:
```bash
make verify-trace
```

#### 3. Verification Rules Configuration
The verification stages and regex log patterns are defined in [trace_rules.yaml](file:///Users/zx1986/Projects/null-ptr-exception/yugabyte-toolkit/trace_rules.yaml). You can modify these patterns or add optional/required stages to customize verification checks:
```yaml
name: "Standard Insert Write Path"
description: "Verifies the standard Raft write behavior in YugabyteDB"
stages:
  - id: "ysql_parse"
    name: "YSQL Parser and Planner"
    pattern: "statement: INSERT INTO test_table"
    required: true
  - id: "raft_append"
    name: "Leader Appends to WAL"
    pattern: "Appending to Raft Log"
    required: true
```

