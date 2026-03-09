import time
import io
import logging
import statistics
from itertools import islice
from concurrent.futures import ThreadPoolExecutor, as_completed
from db_utils import SmartConnectionPool, tune_session

logger = logging.getLogger(__name__)


def _copy_chunk(raw_lines: list[str], pool: SmartConnectionPool, copy_sql: str) -> tuple[int, float]:
    """Copy a chunk of raw CSV lines into the database via COPY FROM STDIN."""
    conn = pool.getconn()
    t0 = time.perf_counter()
    try:
        tune_session(conn)
        buf = io.StringIO("".join(raw_lines))
        with conn.cursor() as cur:
            cur.copy_expert(copy_sql, buf)
            inserted = cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)
    return inserted, time.perf_counter() - t0


def run_parallel(file_path: str, dsn: str, copy_sql: str, workers: int, chunk_size: int) -> dict:
    """
    Stream-reads a CSV file and distributes chunks to a thread pool for parallel COPY.
    Both the DSN and COPY statement are sourced from config.yaml at runtime.
    """
    logger.info(
        "Starting parallel COPY with %d workers, chunk_size=%d ...", workers, chunk_size,
    )

    conn_pool = SmartConnectionPool(dsn=dsn, minconn=workers, maxconn=workers)
    start_time = time.time()
    total_inserted = 0
    chunk_latencies: list[float] = []

    try:
        with open(file_path, "r") as fh:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = []
                while True:
                    chunk = list(islice(fh, chunk_size))
                    if not chunk:
                        break
                    futures.append(executor.submit(_copy_chunk, chunk, conn_pool, copy_sql))

                    if len(futures) >= workers * 2:
                        done = [f for f in futures if f.done()]
                        for f in done:
                            rows, lat = f.result()
                            total_inserted += rows
                            chunk_latencies.append(lat)
                            futures.remove(f)

                for f in as_completed(futures):
                    rows, lat = f.result()
                    total_inserted += rows
                    chunk_latencies.append(lat)
    except Exception as e:
        logger.error("Parallel import failed: %s", e)
        raise
    finally:
        conn_pool.closeall()

    duration = time.time() - start_time
    num_chunks = len(chunk_latencies)

    if chunk_latencies:
        chunk_latencies.sort()
        lat_avg_ms = statistics.mean(chunk_latencies) * 1000
        lat_p95_ms = chunk_latencies[int(num_chunks * 0.95)] * 1000
        lat_p99_ms = chunk_latencies[int(num_chunks * 0.99)] * 1000
    else:
        lat_avg_ms = lat_p95_ms = lat_p99_ms = 0.0

    qps = total_inserted / duration if duration > 0 else 0.0
    tps = num_chunks / duration if duration > 0 else 0.0
    iops = total_inserted / duration if duration > 0 else 0.0

    logger.info("--- Parallel Mode Results ---")
    logger.info("Workers:        %d", workers)
    logger.info("Chunk size:     %d", chunk_size)
    logger.info("Chunks:         %d", num_chunks)
    logger.info("Rows inserted:  %d", total_inserted)
    logger.info("Total time:     %.2f seconds", duration)
    logger.info("QPS:            %.2f rows/sec", qps)
    logger.info("TPS:            %.2f txns/sec", tps)
    logger.info("IOPS:           %.2f row-writes/sec", iops)
    logger.info("Latency avg:    %.2f ms", lat_avg_ms)
    logger.info("Latency p95:    %.2f ms", lat_p95_ms)
    logger.info("Latency p99:    %.2f ms", lat_p99_ms)

    return {
        "label": "Parallel Multi-Thread",
        "workers": workers,
        "chunk_size": chunk_size,
        "rows_inserted": total_inserted,
        "duration_sec": duration,
        "qps": qps,
        "tps": tps,
        "iops": iops,
        "latency_avg_ms": lat_avg_ms,
        "latency_p95_ms": lat_p95_ms,
        "latency_p99_ms": lat_p99_ms,
    }
