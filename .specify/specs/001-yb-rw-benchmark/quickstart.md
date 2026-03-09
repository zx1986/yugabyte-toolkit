# Quickstart: Configuration-Driven Benchmark Tool

This guide walks through setting up the YugabyteDB read/write benchmark using the new YAML-decoupled configuration.

## 1. Setup

Start the local YugabyteDB 1-master, 3-tserver cluster:

```bash
make db-up
```

Install the dependencies within a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install psycopg2-yugabytedb-binary PyYAML
```

## 2. Review the Configuration

By default, the tool expects a `config.yaml` file in the root directory. This file dictates exactly what schemas are created, what CSV generation looks like, and what SQL statements are executed.

Create a default `config.yaml` using the template specified in `contracts/config.md`.

## 3. Generate Data & Standard Write

Generate 1 million rows of mock data (as defined in `config.yaml`) and benchmark standard `pg_copy`:

```bash
# Uses Makefile abstraction which implicitly passes --config config.yaml
make generate ROWS=1000000
make write-single
```

## 4. Parallel Write Benchmark

To test parallel inserts utilizing the YugabyteDB Smart Driver Connection Pool:

```bash
# Using 20 concurrent threads
make write-parallel WORKERS=20
```

## 5. Read Benchmarks

Ensure data is populated. Run the standard unoptimized range queries:

```bash
make read-standard DURATION=60 WORKERS=10
```

Run the optimized range queries (using the explicitly defined Covering Indexes inside `config.yaml`):

```bash
make read-optimized DURATION=60 WORKERS=10
```

## Metrics Output

All modes will output clearly defined QPS, TPS, IOPS, and Latency (Avg, P95, P99) immediately upon completion.
