import psycopg2
from psycopg2 import pool
import logging

logger = logging.getLogger(__name__)


def tune_session(conn):
    """Apply per-session performance tuning suitable for bulk loading."""
    with conn.cursor() as cur:
        cur.execute("SET synchronous_commit = OFF")
        cur.execute("SET session_replication_role = 'replica'")


def init_db_schema(dsn: str, tables: dict):
    """
    Drop and recreate all tables defined in the YAML schema block.
    `tables` is the dict at cfg['schema']['tables'].
    """
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            for key, tbl in tables.items():
                if drop := tbl.get("drop_sql"):
                    cur.execute(drop)
                cur.execute(tbl["ddl"])
                if index_ddl := tbl.get("index_ddl"):
                    cur.execute(index_ddl)
                logger.info("Table '%s' initialized.", tbl["name"])
        conn.commit()


def clear_standard_data(dsn: str, tables: dict):
    """Truncate the standard (write-target) table defined in the YAML schema."""
    standard = tables.get("standard", {})
    truncate_sql = standard.get("truncate_sql")
    if not truncate_sql:
        return
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(truncate_sql)
        conn.commit()
        logger.info("Standard table '%s' truncated.", standard.get("name"))


def populate_optimized_from_standard(dsn: str, tables: dict):
    """
    Drop, recreate, and populate the optimized table from the standard table,
    as defined by the YAML schema block.
    """
    optimized = tables.get("optimized", {})
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            if drop := optimized.get("drop_sql"):
                cur.execute(drop)
            cur.execute(optimized["ddl"])
            if index_ddl := optimized.get("index_ddl"):
                cur.execute(index_ddl)
            if populate_sql := optimized.get("populate_sql"):
                cur.execute(populate_sql)
                logger.info(
                    "Optimized table '%s' populated from standard.", optimized.get("name")
                )
        conn.commit()


class SmartConnectionPool:
    """Thread-safe connection pool backed by YugabyteDB Smart Driver."""

    def __init__(self, dsn: str, minconn: int, maxconn: int):
        self.pool = pool.ThreadedConnectionPool(minconn, maxconn, dsn=dsn)
        logger.info(
            "ThreadedConnectionPool ready (min=%d, max=%d).", minconn, maxconn,
        )

    def getconn(self):
        return self.pool.getconn()

    def putconn(self, conn):
        self.pool.putconn(conn)

    def closeall(self):
        self.pool.closeall()
        logger.info("Connection pool closed.")
