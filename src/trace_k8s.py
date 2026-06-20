import codecs
import threading
from datetime import datetime, timezone


_write_lock = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lines_from_chunks(chunks):
    decoder = codecs.getincrementaldecoder("utf-8")(errors="ignore")
    buffer = ""
    for chunk in chunks:
        if not chunk:
            continue
        buffer += chunk if isinstance(chunk, str) else decoder.decode(chunk)
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            yield line
    buffer += decoder.decode(b"", final=True)
    if buffer:
        yield buffer


def stream_logs_and_filter(
    api_instance,
    namespace: str,
    pod_name: str,
    trace_id: str,
    out_file_path: str,
):
    """Stream K8s pod logs line-by-line, filtering for trace_id and writing matches to disk."""
    print(f"[{utc_now()}] Started log stream for pod: {pod_name}")

    try:
        stream = api_instance.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container="yb-tserver",
            stream=True,
            _preload_content=False,
        )

        log_iterator = stream.stream() if hasattr(stream, "stream") else stream

        with open(out_file_path, "a") as f:
            for line in _lines_from_chunks(log_iterator):
                if trace_id in line:
                    formatted = f"[{utc_now()}] [{pod_name}] {line.strip()}\n"
                    with _write_lock:
                        print(formatted, end="", flush=True)
                        f.write(formatted)
                        f.flush()
    except Exception as e:
        print(f"[{utc_now()}] [ERROR] [{pod_name}] Log stream failed: {e}", flush=True)
