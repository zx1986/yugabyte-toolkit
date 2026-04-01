from unittest.mock import MagicMock, patch

from src.trace_db import execute_insert_with_trace


def test_execute_insert_with_trace_calls_connect_and_commit():
    conn_params = {"host": "localhost", "port": 5433, "dbname": "yugabyte", "user": "yugabyte"}
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("src.trace_db.psycopg2.connect", return_value=mock_conn) as mock_connect:
        execute_insert_with_trace(conn_params, "trace123")

        mock_connect.assert_called_once_with(**conn_params)
        mock_cursor.execute.assert_called_once()
        # Verify the parameterized query contains the trace_id as a parameter
        call_args, call_kwargs = mock_cursor.execute.call_args
        assert "test_table" in call_args[0]
        assert call_args[1] == ("trace123",)
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


def test_execute_insert_uses_parameterized_query():
    """Ensure we use %s placeholder, not f-string interpolation."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("src.trace_db.psycopg2.connect", return_value=mock_conn):
        execute_insert_with_trace({"host": "localhost"}, "trace_abc")

        sql = mock_cursor.execute.call_args[0][0]
        assert "%s" in sql
        assert "trace_abc" not in sql  # Should NOT be interpolated into the query string
