# Tasks: YugabyteDB Configuration-Driven Read/Write Benchmark Tool

**Input**: Design documents from `specs/001-yb-rw-benchmark/`
**Prerequisites**: plan.md, spec.md, research.md, contracts/config.md, contracts/cli.md

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Create `config.yaml` file according to the schema defined in `contracts/config.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T002 [P] Create `src/config_loader.py` to parse `config.yaml` and expose connection, schemas, and queries.
- [x] T003 Update `src/main.py` CLI parser to include `--config` argument and load the YAML file using config_loader.
- [x] T004 Update `src/db_utils.py` to initialize, drop, populate, and truncate dynamic tables defined in the YAML file schema block.

---

## Phase 3: User Story 1 - Benchmark Write Performance (Priority: P1)

- [x] T005 [US1] Update `src/test_data_generator.py` to generate rows dynamically based on the column types defined in `config.yaml`.
- [x] T006 [P] [US1] Update `src/baseline.py` to dynamically execute `queries.write.copy_sql` from the configuration.
- [x] T007 [P] [US1] Update `src/parallel.py` to dynamically execute `queries.write.copy_sql` from the configuration.

---

## Phase 4: User Story 2 - Benchmark Range Query Read Performance (Priority: P1)

- [x] T008 [US2] Update `src/read_bench.py` to accept dynamic SQL query strings and generate `parameters` (e.g. `float_range`) per iteration as dictated by the YAML.
- [x] T009 [US2] Integrate `read_standard` and `read_optimized` routing into `src/main.py` using the loaded YAML query definitions.

---

## Phase N: Polish & Cross-Cutting Concerns

- [x] T010 [P] Update `Makefile` to pass `--config config.yaml` to the python execution targets and adjust documentation.
