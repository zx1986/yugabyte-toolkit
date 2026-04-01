import os
import time
import threading
from datetime import datetime, timezone

from kubernetes import client, config

from .trace_db import execute_insert_with_trace
from .trace_k8s import stream_logs_and_filter


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main():
    print(f"[{utc_now()}] Initializing YugabyteDB Trace Logger Job...")

    try:
        config.load_incluster_config()
    except config.ConfigException:
        print(f"[{utc_now()}] Not running in cluster. Exiting.")
        return

    v1 = client.CoreV1Api()
    namespace = os.getenv("POD_NAMESPACE", "yb-demo")
    out_file = os.getenv("TRACE_OUT_FILE", "/mnt/trace/yugabyte_insert_trace.log")
    trace_id = f"trace_{int(time.time())}"

    pods = ["yb-tserver-0", "yb-tserver-1", "yb-tserver-2"]

    threads = []
    for pod in pods:
        t = threading.Thread(
            target=stream_logs_and_filter,
            args=(v1, namespace, pod, trace_id, out_file),
            daemon=True,
        )
        t.start()
        threads.append(t)

    print(f"[{utc_now()}] Started log streams for {len(pods)} pods, waiting for connection...")
    time.sleep(1)

    conn_params = {
        "host": os.getenv("YB_HOST", "yb-tserver.yb-demo.svc.cluster.local"),
        "port": int(os.getenv("YB_PORT", "5433")),
        "dbname": os.getenv("YB_DBNAME", "yugabyte"),
        "user": os.getenv("YB_USER", "yugabyte"),
        "password": os.getenv("YB_PASSWORD", "password"),
    }

    execute_insert_with_trace(conn_params, trace_id)

    sleep_time = int(os.getenv("TRACE_WAIT_SECONDS", "10"))
    print(f"[{utc_now()}] Waiting {sleep_time} seconds for async logs to arrive...")
    time.sleep(sleep_time)
    print(f"[{utc_now()}] Job completed successfully. Output: {out_file}")


if __name__ == "__main__":
    main()
