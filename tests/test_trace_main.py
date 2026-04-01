from unittest.mock import patch, MagicMock, call

from kubernetes.config import ConfigException

from src.trace_main import main


@patch("src.trace_main.time.sleep")
@patch("src.trace_main.execute_insert_with_trace")
@patch("src.trace_main.stream_logs_and_filter")
@patch("src.trace_main.client.CoreV1Api")
@patch("src.trace_main.config.load_incluster_config")
def test_main_dispatches_streams_and_insert(
    mock_load_config, mock_api_cls, mock_stream, mock_insert, mock_sleep
):
    main()

    mock_load_config.assert_called_once()
    assert mock_insert.call_count == 1
    # 3 tserver pods should be streamed
    assert mock_stream.call_count == 3
    # sleep called at least twice (headstart + wait)
    assert mock_sleep.call_count >= 2


@patch("src.trace_main.time.sleep")
@patch("src.trace_main.execute_insert_with_trace")
@patch("src.trace_main.stream_logs_and_filter")
@patch("src.trace_main.client.CoreV1Api")
@patch("src.trace_main.config.load_incluster_config")
def test_main_passes_trace_id_to_both_layers(
    mock_load_config, mock_api_cls, mock_stream, mock_insert, mock_sleep
):
    main()

    insert_trace_id = mock_insert.call_args[0][1]
    assert insert_trace_id.startswith("trace_")

    for stream_call in mock_stream.call_args_list:
        assert stream_call[0][3] == insert_trace_id


@patch("src.trace_main.config.load_incluster_config", side_effect=ConfigException("not in cluster"))
def test_main_exits_gracefully_outside_cluster(mock_load_config, capsys):
    main()
    captured = capsys.readouterr()
    assert "Not running in cluster" in captured.out
