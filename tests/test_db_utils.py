import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from db_utils import tune_session, SmartConnectionPool

_DSN = "host=localhost port=5433 dbname=yugabyte user=yugabyte password=yugabyte"


class TestTuneSession(unittest.TestCase):
    def test_executes_tuning_queries(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        tune_session(mock_conn)

        calls = [c.args[0] for c in mock_cursor.execute.call_args_list]
        self.assertIn("SET synchronous_commit = OFF", calls)
        self.assertIn("SET session_replication_role = 'replica'", calls)


class TestSmartConnectionPool(unittest.TestCase):
    @patch("db_utils.pool.ThreadedConnectionPool")
    def test_pool_lifecycle(self, mock_pool_cls):
        mock_pool_instance = MagicMock()
        mock_pool_cls.return_value = mock_pool_instance

        sp = SmartConnectionPool(dsn=_DSN, minconn=2, maxconn=4)

        mock_pool_cls.assert_called_once()
        self.assertEqual(mock_pool_instance, sp.pool)

        mock_conn = MagicMock()
        mock_pool_instance.getconn.return_value = mock_conn
        conn = sp.getconn()
        self.assertEqual(conn, mock_conn)

        sp.putconn(conn)
        mock_pool_instance.putconn.assert_called_once_with(mock_conn)

        sp.closeall()
        mock_pool_instance.closeall.assert_called_once()


if __name__ == "__main__":
    unittest.main()
