.PHONY: help db-up db-down generate write-single write-parallel read-standard read-optimized all-tests cluster-up cluster-down cluster-status test-multi-node

# Default configurations
FILE ?= bench.csv
ROWS ?= 1000000
WORKERS ?= 20
DURATION ?= 60
CONFIG ?= config.yaml

help:
	@echo "YugabyteDB Benchmark Tool Makefile"
	@echo ""
	@echo "Infrastructure Commands:"
	@echo "  make db-up           - Start the local YugabyteDB cluster (docker-compose)"
	@echo "  make db-down         - Stop and remove the local YugabyteDB cluster"
	@echo ""
	@echo "Multi-Node Cluster Commands:"
	@echo "  make cluster-up      - Start 3-node yugabyted cluster and wait for readiness"
	@echo "  make cluster-status  - Check status of all cluster nodes"
	@echo "  make cluster-down    - Tear down cluster and wipe all data volumes"
	@echo "  make test-multi-node - Run hash vs range sharding benchmark tests"
	@echo ""
	@echo "Data Generation:"
	@echo "  make generate        - Generate $(ROWS) rows of mock data into $(FILE)"
	@echo ""
	@echo "Write Benchmarks:"
	@echo "  make write-single    - Run baseline single-thread COPY benchmark"
	@echo "  make write-parallel  - Run YugabyteDB Smart Driver parallel COPY benchmark"
	@echo ""
	@echo "Read Benchmarks:"
	@echo "  make read-standard   - Run standard range queries for $(DURATION)s"
	@echo "  make read-optimized  - Run optimized range queries (Covering/Sorted Indexes) for $(DURATION)s"
	@echo ""
	@echo "All Benchmarks:"
	@echo "  make all-tests       - Run generate -> write-parallel -> read-standard -> read-optimized"
	@echo ""
	@echo "Environment Variables (Overrides):"
	@echo "  FILE     (default: bench.csv)"
	@echo "  ROWS     (default: 1000000)"
	@echo "  WORKERS  (default: 20)"
	@echo "  DURATION (default: 60)"
	@echo "  CONFIG   (default: config.yaml)"

db-up:
	docker-compose up -d
	@echo "Waiting 15 seconds for YugabyteDB master election and startup..."
	@sleep 15
	@echo "YugabyteDB cluster is ready."

db-down:
	docker-compose down -v

cluster-up:
	docker compose up -d
	@echo "Waiting 45 seconds for all nodes to join the cluster..."
	@sleep 45
	@echo "Cluster ready. Checking node status:"
	@docker exec yb-node1 bin/yugabyted status --base_dir=/home/yugabyte/yb_data

cluster-status:
	docker exec yb-node1 bin/yugabyted status --base_dir=/home/yugabyte/yb_data

cluster-down:
	docker compose down -v

generate:
	python src/main.py --config $(CONFIG) --mode single --file $(FILE) --generate $(ROWS) --no-init

write-single:
	python src/main.py --config $(CONFIG) --mode single --file $(FILE)

write-parallel:
	python src/main.py --config $(CONFIG) --mode parallel --file $(FILE) --workers $(WORKERS)

read-standard:
	python src/main.py --config $(CONFIG) --mode read_standard --file $(FILE) --workers $(WORKERS) --duration $(DURATION) --no-init

read-optimized:
	python src/main.py --config $(CONFIG) --mode read_optimized --file $(FILE) --workers $(WORKERS) --duration $(DURATION) --no-init

all-tests: db-up generate write-parallel read-standard read-optimized
	@echo "All benchmark tests completed successfully."

test-multi-node: cluster-up
	uv run python -m pytest tests/test_multi_node_perf.py -v -s
