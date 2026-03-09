# Implementation Plan: yb-multi-node

**Branch**: `002-yb-multi-node` | **Date**: 2026-03-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-yb-multi-node/spec.md`

## Summary

This feature involves creating a local 3-node YugabyteDB cluster using Docker Compose and the official LTS image (`yugabytedb/yugabyte:2024.2.8.0-b85`). Once the cluster is running, identical schemas for hash-sharded and range-sharded tables will be instantiated to benchmark and compare range query performance against both structures. Robust testing strategies will be implemented to automatically wipe existing data on startup and gracefully handle connection drops or node failures during data loading.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `psycopg2-yugabytedb-binary`, Docker, `pytest`
**Storage**: YugabyteDB (yugabytedb/yugabyte:2024.2.8.0-b85)
**Testing**: pytest
**Target Platform**: Local Docker Environment via `docker compose`
**Project Type**: CLI tool & Benchmarking testing framework
**Performance Goals**: Observe latency differences on range queries between Hash-sharded vs Range-sharded tables.
**Constraints**: Must use specified LTS image, handle failure scenarios effectively.
**Scale/Scope**: 3 nodes local cluster, benchmarking scripts for inserts and reads.

## Implementation Sequence

The following sequence of tasks must be executed to fulfill this feature. Each step references the specific technical details defined during the planning phase.

### Step 1: Orchestrate the Multi-Node Cluster
Update the existing project `docker-compose.yaml` to define the 3-node topology instead of the existing setup.
- **Goal**: Spin up `yb-node1`, `yb-node2`, and `yb-node3` using the specified LTS image.
- **Reference**: See [`research.md`](./research.md) (Section: *Multi-Node Configuration*) for the required startup flags (`--advertise_address`, `--cloud_location`, `--join`).
- **Reference**: See [`quickstart.md`](./quickstart.md) for the expected `docker compose up -d` wipe-on-startup behavior.

### Step 2: Implement Makefile Commands
Add helper targets to the `Makefile` to simplify starting, stopping, and checking the cluster status.
- **Goal**: Provide `make cluster-up`, `make cluster-down`, and `make test`.
- **Reference**: See [`quickstart.md`](./quickstart.md) for the exact Docker commands to run for status checks and teardown.

### Step 3: Define the Database Schemas
Implement the database initialization logic (either via SQL files or Python DB utility functions) to create the required benchmark tables.
- **Goal**: Create the hash-sharded and range-sharded tables.
- **Reference**: See [`data-model.md`](./data-model.md) for the exact schema definitions and primary key configurations for `users_hash` and `users_range`.

### Step 4: Develop the Benchmark Script
Create the `tests/test_multi_node_perf.py` script to perform data generation, execution, and performance measurement.
- **Goal**: Insert data and perform range queries against both table types, ensuring connection drops are handled.
- **Reference**: See [`research.md`](./research.md) (Section: *Comparison Testing Strategy*) for the query design.
- **Reference**: See [`spec.md`](./spec.md) (Section: *Edge Cases*) for the requirement to implement automatic retries during connection drops and node failures.

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. CLI First**: Configuration and target node will be passed via CLI arguments to the benchmarking scripts.
- [x] **II. Performance Observability**: Python tests will record and output duration and throughput for queries across both table types.
- [x] **III. Reliable Reproducibility**: `docker-compose` leverages named volumes that are purged effectively on teardown.
- [x] **IV. Safe Concurrency**: Standard pooling connections will be utilized by `psycopg2` under load to prevent exhaustion when mimicking disconnects.

## Project Structure

### Documentation (this feature)

```text
specs/002-yb-multi-node/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# Option 1: Single project (DEFAULT)
tests/
├── conftest.py
├── test_multi_node_perf.py    # Main benchmarking script for Hash vs Range
docker-compose.yaml            # Updated 3-node cluster definition
Makefile                       # Targets for clustering up/down and tests
```

**Structure Decision**: A simple project extending the existing source layout. The `docker-compose.yaml` will reside at the root. New tests highlighting the cluster multi-node behaviour will reside in `tests/test_multi_node_perf.py`.

## Complexity Tracking

No violations found. Basic structural adjustments using standard tooling.
