# Research: YugabyteDB Benchmark Tool YAML Decoupling

## Purpose
Resolve architectural unknowns regarding decoupling database schemas, SQL queries, and connections from the Python logic into a YAML configuration format, while preserving the explicitly requested `RANGE_QUERY_OPTIMIZED` schema design.

## Technical Context Unknowns Resolved

### 1. How to structure the YAML configuration for schemas?
- **Decision**: The YAML config will define a `schema.tables` dictionary where each key represents a logical table purpose (e.g., `standard`, `optimized`). Each entry will contain the explicit `ddl` (CREATE TABLE), `index_ddl` (CREATE INDEX), `drop_sql`, and `truncate_sql`.
- **Rationale**: This allows the Python script to blindly loop through `schema.tables.values()` to initialize or truncate the database, making it agnostic to the actual table names or complex covering index structures defined by the user.

### 2. How to parameterize ranges for SQL queries in YAML?
- **Decision**: The `queries` block will contain the raw SQL with standard `%s` placeholders. It will also contain a `parameters` list defining the generation rules (e.g., `type: float_range`, `min: 0.0`, `max: 50.0`). The Python worker will look up the parameter type and generate the random pair before executing the query.
- **Rationale**: Keeps the Python code generic `cur.execute(sql, tuple(params))` while allowing the config to dictate both the exact query text and rules for generating random lookup values.

### 3. How to decouple data generation?
- **Decision**: Define a `data_generation.columns` list in YAML that specifies the data type for each CSV column (`sequential_int`, `random_string`, `composite`, `random_float`, `random_timestamp`). The Python generator will iterate this list to construct each row.
- **Rationale**: If the user changes the schema to add a new column in `config.yaml`, the Python generator will automatically adapt without code changes.

### 4. How to preserve RANGE_QUERY_OPTIMIZED design?
- **Decision**: The `config.yaml` will ship with a default structure that exactly implements the YugabyteDB optimized covering index (`idx_score_name` with `score DESC, name ASC` and `INCLUDE (email, created_at)`). The Python logic will still expose `--mode read_optimized` which looks up `queries.read_optimized` in the YAML.
- **Rationale**: Satisfies the explicit user requirement to retain the optimized design comparison while moving the actual SQL text out of the `.py` files.
