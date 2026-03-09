# Implementation Plan: Configuration-Driven YugabyteDB Benchmark Tool

**Branch**: `001-yb-rw-benchmark` | **Date**: 2026-03-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-yb-rw-benchmark/spec.md`

## Summary

Refactor the existing YugabyteDB CSV benchmark tool to be entirely configuration-driven via a YAML file (`config.yaml`). This decouples the database connection strings, table schemas (standard vs. optimized), data generation constraints, and read/write SQL queries from the Python logic, allowing users to benchmark varying database designs without altering code. The explicitly required `RANGE_QUERY_OPTIMIZED` layout will be maintained as the default configuration.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: `psycopg2-yugabytedb-binary`, `argparse`, `PyYAML`, YugabyteDB Docker images.  
**Storage**: Local Docker Compose (1 master, 3 tservers) limited to 3GiB storage.  
**Testing**: Docker Compose local run and manual script validation against the new YAML parser.  
**Target Platform**: Local developer workstation (macOS).  
**Project Type**: CLI Data Benchmarking Tool.  
**Performance Goals**: Support high-throughput parsing and execution; the YAML loading overhead must only occur once at startup.  
**Constraints**: Must use Python standard library threads for parallel copy, and standard `psycopg2` driver logic. Logic must be generic enough to execute arbitrary SQL read queries defined in YAML.

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. CLI First**: Configuration strictly via CLI arguments, utilizing `--config` to point to the YAML definition.
- [x] **II. Performance Observability**: The tool will continue to emit distinct read/write metrics (QPS, TPS, Latency, IOPS).
- [x] **III. Reliable Reproducibility**: Setup includes clearing data and explicit schema initialization driven dynamically by the YAML config.
- [x] **IV. Safe Concurrency**: Connection pool limits dictate max concurrency for the dynamic queries via bounded `ThreadPoolExecutor`.

## Project Structure

### Documentation (this feature)

```text
specs/001-yb-rw-benchmark/
├── plan.md              # This file
├── research.md          # Technical decisions on YAML layout
├── data-model.md        # YAML Data model expectations
├── contracts/cli.md     # CLI argument contract
├── contracts/config.md  # YAML structure contract
└── quickstart.md        # Usage instructions
```

### Source Code (repository root)

```text
/
├── docker-compose.yaml  
├── config.yaml          # [NEW] Contains DB connection, schemas, and query definitions
├── src/
│   ├── main.py          # [MODIFY] Parse YAML config and pass context to runners
│   ├── config_loader.py # [NEW] Parses and validates the YAML configuration
│   ├── db_utils.py      # [MODIFY] Dynamic schema init based on YAML config loops
│   ├── baseline.py      # [MODIFY] Decoupled COPY statement
│   ├── parallel.py      # [MODIFY] Decoupled COPY statement
│   ├── read_bench.py    # [MODIFY] Execute dynamic read SQL from config matching parameters
│   └── test_data_generator.py # [MODIFY] Generate CSV dynamically based on YAML schema column types
└── Makefile             # [MODIFY] Pass the config argument
```

**Structure Decision**: Retaining the flat Python module layout in `src/`, introducing `config_loader.py` to handle `PyYAML` ingestion and pass a parsed dict to the existing workers. `config.yaml` sits at the repo root.

## Verification Plan

### Manual Verification
1. Boot the YugabyteDB cluster: `make db-up`
2. Create/update the `config.yaml` file to alter a column name (e.g., `user_email` instead of `email`).
3. Run data generation: `make generate` -> Verify the CSV has the updated column data.
4. Execute benchmark sequence: `make all-tests`
5. Verify output metrics correctly output values without SQL hardcoding errors, proving the Python code successfully read the YAML overrides.
