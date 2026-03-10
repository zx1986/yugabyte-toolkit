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
