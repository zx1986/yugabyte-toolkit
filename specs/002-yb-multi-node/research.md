# Research & Decisions: yb-multi-node

## Technical Context Unknowns Resolved

### 1. LTS Image Compatibility
- **Decision**: Use `yugabytedb/yugabyte:2024.2.8.0-b85` for all nodes in the `docker-compose.yaml`.
- **Rationale**: The user explicitly requested this LTS image version for stability and alignment with project standards.
- **Alternatives considered**: The newer `2.21.1.0-b271` from the blog post was rejected in favor of the LTS version.

### 2. Multi-Node Configuration
- **Decision**: Define a 3-node cluster in `docker-compose.yaml` using `bin/yugabyted start` with `--advertise_address`, `--cloud_location` (zone1, zone2, zone3), and `yb-node1` as the join target for the others.
- **Rationale**: This is the recommended local multi-node architecture according to the referenced blog post, simulating a realistic distributed topology. Volume mounts will be parameterized or tracked via Docker named volumes to allow clean wipes on startup.

### 3. Comparison Testing Strategy
- **Decision**: Create two structurally identical tables (`users_hash` and `users_range`) but apply different primary key configurations:
  - `users_hash`: `id UUID PRIMARY KEY HASH` (or default YB behavior).
  - `users_range`: `id UUID PRIMARY KEY ASC` (range sharded).
- **Rationale**: The user wants to compare the performance of a range query on both table types. A Python benchmarking script or basic SQL script containing `EXPLAIN ANALYZE` or a timed execution loop will perform identical range queries (e.g., `WHERE created_at BETWEEN ...`) against both tables.
- **Alternatives considered**: Using pgbench was considered, but writing custom SQL via the existing Python harness gives more explicit control over the query and output format required.

## Constitution Verification
All research decisions align with the YugabyteDB CSV Importer Constitution:
- **Reproducibility**: `docker compose down -v` will ensure clean data volume wipes.
- **Safe Concurrency / Observability**: Using the established `db_utils` and `psycopg2` driver in Python will yield the required structured logging metrics.
