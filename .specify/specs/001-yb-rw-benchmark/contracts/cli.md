# CLI Contract: YugabyteDB Benchmark Tool

## Application Interface 

The main entry point is `src/main.py`.

### Global Arguments
- `--config <path>`: Required. Path to the YAML configuration file defining the database schema, queries, and connection settings. Default: `config.yaml`.
- `--file <path>`: Required. Path to the generated or existing CSV file to benchmark.
- `--generate <int>`: Optional. Number of rows to generate into the CSV file before execution. Will overwrite the file mapping based on the configuration logic.
- `--no-init`: Optional. Skip recreating the schema, only truncating existing tables. Useful for consecutive read tests.
- `--mode <string>`: Required. Defines the benchmark mode:
  - `single`: Traditional single-threaded `COPY` write.
  - `parallel`: Multi-threaded pool `COPY` write (YugabyteDB Smart Driver).
  - `read_standard`: Traditional range query read performance.
  - `read_optimized`: Optimized range query.

### Parallel / Read Specific Arguments
- `--workers <int>`: Optional. Default 10. Number of concurrent threads for parallel writes or concurrent read clients.
- `--chunk-size <int>`: Optional. Default 10000. Rows per internal batch for writes.
- `--duration <int>`: Optional. Default 60. Seconds to execute the read benchmark loops.

### Command Examples
**Write Benchmarks**
```bash
# Generate 1M rows and test standard copy using local configuration
python src/main.py --config config.yaml --mode single --file data.csv --generate 1000000

# Test parallel copy with 20 workers
python src/main.py --config config.yaml --mode parallel --file data.csv --workers 20
```

**Read Benchmarks**
```bash
# Test read latency and throughput on standard table for 60 seconds
python src/main.py --config config.yaml --mode read_standard --file data.csv --workers 10 --duration 60 --no-init

# Test read latency and throughput on optimized indexes
python src/main.py --config config.yaml --mode read_optimized --file data.csv --workers 10 --duration 60 --no-init
```
