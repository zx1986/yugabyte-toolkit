import psycopg2
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_insert_with_trace(conn_params: dict, trace_id: str):
    """Execute a single INSERT with the given trace_id for later log correlation."""
    print(f"[{utc_now()}] Connecting to Database...")
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    print(f"[{utc_now()}] Executing INSERT with trace_id: {trace_id}")
    cur.execute(
        "INSERT INTO test_table (id, val) VALUES (gen_random_uuid(), %s)",
        (trace_id,),
    )
    conn.commit()

    cur.close()
    conn.close()
    print(f"[{utc_now()}] Database insert completed.")
