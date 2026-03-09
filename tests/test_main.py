import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import main

_CFG = {
    "database": {
        "host": "localhost", "port": 5433,
        "dbname": "yugabyte", "user": "yugabyte", "password": "yugabyte",
    },
    "schema": {
        "tables": {
            "standard": {
                "name": "test_data",
                "ddl": "CREATE TABLE test_data (id int PRIMARY KEY);",
                "drop_sql": "DROP TABLE IF EXISTS test_data;",
                "truncate_sql": "TRUNCATE TABLE test_data;",
            }
        }
    },
    "queries": {
        "write": {"copy_sql": "COPY test_data FROM STDIN WITH (FORMAT CSV)"},
        "read_standard": {
            "sql": "SELECT 1;",
            "parameters": [{"type": "float_range", "min": 0, "max": 50, "range_size_min": 5, "range_size_max": 50}],
        },
        "read_optimized": {
            "sql": "SELECT 1;",
            "parameters": [{"type": "float_range", "min": 0, "max": 50, "range_size_min": 5, "range_size_max": 50}],
        },
    },
    "data_generation": {
        "format": "csv",
        "columns": [
            {"name": "id", "type": "sequential_int"},
        ],
    },
}


class TestMainCLI(unittest.TestCase):
    @patch("main.run_baseline")
    @patch("main.init_db_schema")
    @patch("main.load_config", return_value=_CFG)
    def test_single_mode(self, mock_cfg, mock_init, mock_baseline):
        mock_baseline.return_value = {"rows_inserted": 100, "qps": 100.0}
        with patch("sys.argv", ["main.py", "--mode", "single", "--file", "test.csv"]):
            main()
        mock_init.assert_called_once()
        mock_baseline.assert_called_once()

    @patch("main.run_parallel")
    @patch("main.init_db_schema")
    @patch("main.load_config", return_value=_CFG)
    def test_parallel_mode(self, mock_cfg, mock_init, mock_parallel):
        mock_parallel.return_value = {"rows_inserted": 100, "qps": 200.0}
        with patch("sys.argv", [
            "main.py", "--mode", "parallel", "--file", "test.csv",
            "--workers", "4", "--chunk-size", "50",
        ]):
            main()
        mock_parallel.assert_called_once()

    @patch("main.run_baseline")
    @patch("main.clear_standard_data")
    @patch("main.init_db_schema")
    @patch("main.load_config", return_value=_CFG)
    def test_no_init_flag(self, mock_cfg, mock_init, mock_clear, mock_baseline):
        mock_baseline.return_value = {"rows_inserted": 10, "qps": 100.0}
        with patch("sys.argv", [
            "main.py", "--mode", "single", "--file", "t.csv", "--no-init",
        ]):
            main()
        mock_init.assert_not_called()
        mock_clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
