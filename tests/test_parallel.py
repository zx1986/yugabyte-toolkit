import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parallel import _copy_chunk, run_parallel

_DSN = "host=localhost port=5433 dbname=yugabyte user=yugabyte password=yugabyte"
_COPY_SQL = "COPY test_data FROM STDIN WITH (FORMAT CSV)"


class TestCopyChunk(unittest.TestCase):
    @patch("parallel.tune_session")
    def test_copy_chunk_returns_rowcount(self, mock_tune):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 50
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        raw_lines = ["1,a,a@x.com,1.0,2025-01-01 00:00:00\n"] * 50
        rows, latency = _copy_chunk(raw_lines, mock_pool, _COPY_SQL)

        self.assertEqual(rows, 50)
        self.assertGreaterEqual(latency, 0)
        mock_cursor.copy_expert.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    @patch("parallel.tune_session")
    def test_copy_chunk_rollback_on_error(self, mock_tune):
        mock_cursor = MagicMock()
        mock_cursor.copy_expert.side_effect = Exception("db error")
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with self.assertRaises(Exception):
            _copy_chunk(["1,a,a@x.com,1.0,2025-01-01\n"], mock_pool, _COPY_SQL)

        mock_conn.rollback.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)


class TestRunParallel(unittest.TestCase):
    @patch("parallel.SmartConnectionPool")
    def test_returns_metrics(self, mock_pool_cls):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 5
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_pool_cls.return_value = mock_pool

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            for i in range(10):
                f.write(f"{i},n,e@x.com,1.0,2025-01-01 00:00:00\n")
            tmp_path = f.name

        try:
            result = run_parallel(tmp_path, _DSN, _COPY_SQL, workers=2, chunk_size=5)
            self.assertIn("rows_inserted", result)
            self.assertIn("qps", result)
            self.assertIn("latency_avg_ms", result)
            self.assertGreater(result["duration_sec"], 0)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
