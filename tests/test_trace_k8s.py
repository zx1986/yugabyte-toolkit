import tempfile
from unittest.mock import MagicMock, patch

from src.trace_k8s import stream_logs_and_filter


def test_stream_logs_filters_by_trace_id():
    mock_api = MagicMock()
    mock_api.read_namespaced_pod_log.return_value = [
        b"Noise log without trace\n",
        b"Target log with trace123 inside it\n",
        b"Another noise log\n",
    ]

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as tmp:
        tmp_path = tmp.name

    stream_logs_and_filter(mock_api, "yb-demo", "yb-tserver-0", "trace123", tmp_path)

    with open(tmp_path) as f:
        content = f.read()

    assert "Noise" not in content
    assert "trace123" in content
    assert "[yb-tserver-0]" in content


def test_stream_logs_prepends_utc_timestamp():
    mock_api = MagicMock()
    mock_api.read_namespaced_pod_log.return_value = [
        b"match trace_xyz here\n",
    ]

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as tmp:
        tmp_path = tmp.name

    with patch("src.trace_k8s.utc_now", return_value="2026-04-02T00:00:00+00:00"):
        stream_logs_and_filter(mock_api, "ns", "pod-0", "trace_xyz", tmp_path)

    with open(tmp_path) as f:
        content = f.read()

    assert "[2026-04-02T00:00:00+00:00]" in content
    assert "[pod-0]" in content


def test_stream_logs_empty_chunks_skipped():
    mock_api = MagicMock()
    mock_api.read_namespaced_pod_log.return_value = [
        b"",
        None,
        b"has trace_id_1 line\n",
    ]

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as tmp:
        tmp_path = tmp.name

    stream_logs_and_filter(mock_api, "ns", "pod-0", "trace_id_1", tmp_path)

    with open(tmp_path) as f:
        lines = f.readlines()

    assert len(lines) == 1
    assert "trace_id_1" in lines[0]
