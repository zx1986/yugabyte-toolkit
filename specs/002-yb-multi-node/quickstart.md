# Quickstart: Multi-Node YugabyteDB Benchmark

This guide outlines how to start the local multi-node environment and run the comparison tests.

## 1. Start the Cluster

To initialize the 3-node YugabyteDB cluster locally using the LTS image (`2024.2.8.0-b85`):

```bash
docker compose up -d
```
Docker Compose will download the image and initialize `yb-node1`, `yb-node2`, and `yb-node3`, automatically wiping any previous anonymous container data volumes. Wait approximately 30-45 seconds for all nodes to become healthy and join the cluster ring.

## 2. Verify Cluster Status

You can verify the cluster health using `yugabyted status` on the primary node:

```bash
docker exec yb-node1 bin/yugabyted status --base_dir=/home/yugabyte/yb_data
```

## 3. Run the Verification Tests

Execute the benchmark script (e.g., Python `pytest` harness or CLI script based on `test_main.py` enhancements):

```bash
# Example invocation (exact command to be determined in Implementation)
python -m pytest tests/test_multi_node_perf.py -v
```

This test will:
1. Re-initialize the test tables (`users_hash` and `users_range`).
2. Seed thousands of rows of realistic data.
3. Perform range queries against both table structures.
4. Output comparative response time metrics showing the latency differences.

## 4. Teardown

To shut down the cluster and clean up volumes:

```bash
docker compose down -v
```
