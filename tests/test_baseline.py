import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from baseline import run_baseline

_DSN = "host=localhost port=5433 dbname=yugabyte user=yugabyte password=yugabyte"
_COPY_SQL = "COPY test_data FROM STDIN WITH (FORMAT CSV)"


class TestRunBaseline(unittest.TestCase):
    @patch("baseline.tune_session")
    @patch("baseline.psycopg2.connect")
    def test_returns_metrics(self, mock_connect, mock_tune):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 100
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_connect.return_value = mock_conn

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            for i in range(100):
                f.write(f"{i},name,email@x.com,1.0,2025-01-01 00:00:00\n")
            tmp_path = f.name

        try:
            result = run_baseline(tmp_path, _DSN, _COPY_SQL)
            self.assertEqual(result["rows_inserted"], 100)
            self.assertIn("qps", result)
            self.assertIn("tps", result)
            self.assertIn("iops", result)
            self.assertIn("latency_ms", result)
            mock_cursor.copy_expert.assert_called_once()
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
