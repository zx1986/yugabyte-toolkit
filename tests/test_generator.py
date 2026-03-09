import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from test_data_generator import generate_test_data

# The new API requires a columns spec list
_COLUMNS = [
    {"name": "id", "type": "sequential_int"},
    {"name": "name", "type": "random_string", "length": 10},
    {"name": "email", "type": "composite", "pattern": "{name}@example.com"},
    {"name": "score", "type": "random_float", "min": 0.0, "max": 100.0},
    {"name": "created_at", "type": "random_timestamp", "days_back": 30},
]


class TestGenerateTestData(unittest.TestCase):
    def _make_tmp(self):
        """Return a temp path that does NOT yet exist."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
        os.unlink(tmp_path)
        return tmp_path

    def test_generates_correct_row_count(self):
        tmp_path = self._make_tmp()
        try:
            generate_test_data(tmp_path, num_rows=100, columns=_COLUMNS)
            with open(tmp_path) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 100)
        finally:
            os.unlink(tmp_path)

    def test_csv_columns(self):
        tmp_path = self._make_tmp()
        try:
            generate_test_data(tmp_path, num_rows=5, columns=_COLUMNS)
            with open(tmp_path) as f:
                for line in f:
                    parts = line.strip().split(",")
                    self.assertEqual(len(parts), 5, f"Expected 5 columns, got: {parts}")
                    self.assertTrue(parts[0].isdigit())
                    self.assertIn("@example.com", parts[2])
        finally:
            os.unlink(tmp_path)

    def test_skips_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write("existing\n")
            tmp_path = tmp.name
        try:
            generate_test_data(tmp_path, num_rows=10, columns=_COLUMNS)
            with open(tmp_path) as f:
                content = f.read()
            self.assertEqual(content, "existing\n")
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
