import time
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from db_utils import SmartConnectionPool
from config_loader import generate_query_params

logger = logging.getLogger(__name__)


def _execute_query(
    pool: SmartConnectionPool,
    sql: str,
    parameters_spec: list[dict],
    latencies: list[float],
) -> int:
    """Execute a single configured range query and record its latency."""
    params = generate_query_params(parameters_spec)
    conn = pool.getconn()
    try:
        t0 = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.rowcount
        latencies.append((time.perf_counter() - t0) * 1000.0)
        return rows
    finally:
        pool.putconn(conn)


def _run_read_bench(
    dsn: str,
    sql: str,
    parameters_spec: list[dict],
    workers: int,
    duration_sec: int,
    label: str,
) -> dict:
    """
    Drive concurrent read queries for `duration_sec` seconds using a pool of
    `workers` concurrent clients. The SQL and parameters are fully config-driven.
    """
    conn_pool = SmartConnectionPool(dsn=dsn, minconn=workers, maxconn=workers)
    latencies: list[float] = []
    total_queries = 0
    start = time.time()
    deadline = start + duration_sec

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            pending: set = set()
            while time.time() < deadline:
                while len(pending) < workers * 2 and time.time() < deadline:
                    f = executor.submit(
                        _execute_query, conn_pool, sql, parameters_spec, latencies
                    )
                    pending.add(f)

                done = {f for f in pending if f.done()}
                for f in done:
                    f.result()
                    total_queries += 1
                    pending -= {f}

            for f in as_completed(pending):
                f.result()
                total_queries += 1
    finally:
        conn_pool.closeall()

    elapsed = time.time() - start

    if latencies:
        latencies.sort()
        avg_ms = statistics.mean(latencies)
        p95_ms = latencies[int(len(latencies) * 0.95)]
        p99_ms = latencies[int(len(latencies) * 0.99)]
    else:
        avg_ms = p95_ms = p99_ms = 0.0

    qps = total_queries / elapsed if elapsed > 0 else 0.0
    tps = qps
    iops = (total_queries * 100) / elapsed if elapsed > 0 else 0.0

    logger.info("--- %s Read Results ---", label)
    logger.info("Workers:       %d", workers)
    logger.info("Duration:      %.2f seconds", elapsed)
    logger.info("Total queries: %d", total_queries)
    logger.info("QPS:           %.2f queries/sec", qps)
    logger.info("TPS:           %.2f txns/sec", tps)
    logger.info("IOPS (est.):   %.2f row-reads/sec", iops)
    logger.info("Latency avg:   %.2f ms", avg_ms)
    logger.info("Latency p95:   %.2f ms", p95_ms)
    logger.info("Latency p99:   %.2f ms", p99_ms)

    return {
        "label": label,
        "qps": qps,
        "tps": tps,
        "iops": iops,
        "latency_avg_ms": avg_ms,
        "latency_p95_ms": p95_ms,
        "latency_p99_ms": p99_ms,
        "total_queries": total_queries,
        "duration_sec": elapsed,
    }


def run_standard_read(dsn: str, sql: str, parameters_spec: list[dict], workers: int, duration_sec: int) -> dict:
    """Benchmark standard range queries using config-driven SQL."""
    return _run_read_bench(dsn, sql, parameters_spec, workers, duration_sec, "Standard Read")


def run_optimized_read(dsn: str, sql: str, parameters_spec: list[dict], workers: int, duration_sec: int) -> dict:
    """Benchmark optimized range queries using config-driven SQL (covering index)."""
    return _run_read_bench(dsn, sql, parameters_spec, workers, duration_sec, "Optimized Read")
