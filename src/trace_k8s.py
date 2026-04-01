from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stream_logs_and_filter(
    api_instance,
    namespace: str,
    pod_name: str,
    trace_id: str,
    out_file_path: str,
):
    """Stream K8s pod logs line-by-line, filtering for trace_id and writing matches to disk."""
    print(f"[{utc_now()}] Started log stream for pod: {pod_name}")

    stream = api_instance.read_namespaced_pod_log(
        name=pod_name,
        namespace=namespace,
        container="yb-tserver",
        stream=True,
        _preload_content=False,
    )

    log_iterator = stream.stream() if hasattr(stream, "stream") else stream

    with open(out_file_path, "a") as f:
        for chunk in log_iterator:
            if not chunk:
                continue
            line = chunk if isinstance(chunk, str) else chunk.decode("utf-8", errors="ignore")
            if trace_id in line:
                formatted = f"[{utc_now()}] [{pod_name}] {line.strip()}\n"
                f.write(formatted)
                f.flush()
