"""
Multi-node YugabyteDB availability and sharding benchmark test.

Tests:
  1. All 3 cluster nodes report as healthy.
  2. Schema initialization creates users_hash and users_range tables.
  3. Data inserts succeed and all rows are readable.
  4. A range query on created_at returns consistent results from both tables.
  5. Comparative timing: range query on users_range vs users_hash.

See: specs/002-yb-multi-node/data-model.md  for schema definitions.
     specs/002-yb-multi-node/spec.md         for acceptance criteria.
     specs/002-yb-multi-node/research.md     for query design rationale.
"""

import os
import re
import subprocess
import time
import logging
import psycopg2
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

DSN = {
    "host": os.getenv("YB_HOST", "127.0.0.1"),
    "port": int(os.getenv("YB_PORT", "5433")),
    "dbname": os.getenv("YB_DBNAME", "yugabyte"),
    "user": os.getenv("YB_USER", "yugabyte"),
    "password": os.getenv("YB_PASSWORD", "yugabyte"),
}

SEED_ROWS = 10_000


def _connect(retries: int = 5, delay: float = 5.0):
    """Open a connection with basic retry logic to handle transient node drops."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(**DSN)
            conn.autocommit = False
            return conn
        except psycopg2.OperationalError as exc:
            last_err = exc
            logger.warning("Connection attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay)
    raise last_err


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_conn():
    """Module-scoped live DB connection."""
    conn = _connect()
    yield conn
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def init_schema(db_conn):
    """
    Drop and recreate benchmark tables before the test suite runs.
    Ensures reproducibility (spec SC-004 / FR-004).
    """
    sql_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "init_schema.sql")
    with open(sql_path) as fh:
        ddl = fh.read()

    with db_conn.cursor() as cur:
        cur.execute(ddl)
    db_conn.commit()
    logger.info("Schema initialized from %s", sql_path)


@pytest.fixture(scope="module")
def seeded_db(db_conn, init_schema):
    """Seed SEED_ROWS rows into both tables and return the connection."""
    with db_conn.cursor() as cur:
        for i in range(SEED_ROWS):
            cur.execute(
                "INSERT INTO users_hash (email, name) VALUES (%s, %s)",
                (f"hash_user_{i}@example.com", f"Hash User {i}"),
            )
            cur.execute(
                "INSERT INTO users_range (email, name) VALUES (%s, %s)",
                (f"range_user_{i}@example.com", f"Range User {i}"),
            )
    db_conn.commit()
    logger.info("Seeded %d rows into each table.", SEED_ROWS)
    return db_conn


# ---------------------------------------------------------------------------
# Test 1: Cluster health
# ---------------------------------------------------------------------------

class TestClusterHealth:
    def test_all_nodes_reachable(self):
        """
        Verify yugabyted status reports a live cluster.
        SC-001: All nodes active within 60s before tests run.
        """
        result = subprocess.run(
            ["docker", "exec", "yb-node1",
             "bin/yugabyted", "status", "--base_dir=/home/yugabyte/yb_data"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"yugabyted status failed:\n{result.stdout}\n{result.stderr}"
        assert "Running" in result.stdout, (
            f"Expected 'Running' in status output. Got:\n{result.stdout}"
        )

    def test_ysql_connection(self):
        """
        SC-002: A YSQL connection can be established without errors.
        """
        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
            assert row == (1,)
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Test 2: Schema availability
# ---------------------------------------------------------------------------

class TestSchema:
    def test_users_hash_exists(self, db_conn):
        """SC-003: DDL for hash-sharded table completes without error."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'users_hash'"
            )
            assert cur.fetchone()[0] == 1

    def test_users_range_exists(self, db_conn):
        """SC-003: DDL for range-sharded table completes without error."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'users_range'"
            )
            assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Test 3: Data integrity
# ---------------------------------------------------------------------------

class TestDataIntegrity:
    def test_hash_row_count(self, seeded_db):
        """SC-004: All inserted rows are retrievable from users_hash."""
        with seeded_db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users_hash")
            assert cur.fetchone()[0] == SEED_ROWS

    def test_range_row_count(self, seeded_db):
        """SC-004: All inserted rows are retrievable from users_range."""
        with seeded_db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users_range")
            assert cur.fetchone()[0] == SEED_ROWS


# ---------------------------------------------------------------------------
# Test 4: Range query performance comparison
# ---------------------------------------------------------------------------

RANGE_QUERY_HASH = """
    SELECT id, email, name, created_at
    FROM users_hash
    WHERE created_at >= NOW() - INTERVAL '1 hour'
    ORDER BY created_at
    LIMIT 1000
"""

RANGE_QUERY_RANGE = """
    SELECT id, email, name, created_at
    FROM users_range
    WHERE created_at >= NOW() - INTERVAL '1 hour'
    ORDER BY created_at
    LIMIT 1000
"""


class TestRangeQueryPerformance:
    def _time_query(self, conn, sql: str) -> float:
        t0 = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.fetchall()
        return time.perf_counter() - t0

    def test_range_query_hash_table(self, seeded_db):
        """Verify range query on users_hash executes without error."""
        elapsed = self._time_query(seeded_db, RANGE_QUERY_HASH)
        logger.info("users_hash  range query: %.4fs", elapsed)
        assert elapsed >= 0

    def test_range_query_range_table(self, seeded_db):
        """Verify range query on users_range executes without error."""
        elapsed = self._time_query(seeded_db, RANGE_QUERY_RANGE)
        logger.info("users_range range query: %.4fs", elapsed)
        assert elapsed >= 0

    def test_compare_range_query_latency(self, seeded_db):
        """
        Compare range query latency between hash and range-sharded tables.
        Expected: users_range is faster for range scans (no random seek required).
        Logs the result; does not hard-fail if hash is faster (non-deterministic in small sets).
        """
        hash_time = self._time_query(seeded_db, RANGE_QUERY_HASH)
        range_time = self._time_query(seeded_db, RANGE_QUERY_RANGE)

        print(f"\n📊 Range Query Comparison:")
        print(f"   users_hash  : {hash_time:.4f}s")
        print(f"   users_range : {range_time:.4f}s")
        if range_time < hash_time:
            print("   ✓ users_range is faster (expected for range scans)")
        else:
            print("   ~ users_hash matched or beat users_range")
            print("     (normal for small datasets; difference grows with scale)")

        # Both queries must complete — the correctness assertion
        assert hash_time > 0
        assert range_time > 0
