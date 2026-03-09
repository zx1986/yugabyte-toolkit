import os
import random
import string
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_LETTERS = string.ascii_letters


def _generate_value(col: dict, row_index: int, prev_values: dict) -> str:
    """Generate a single CSV field value given a column spec dict."""
    ctype = col["type"]

    if ctype == "sequential_int":
        return str(row_index)

    elif ctype == "random_string":
        length = col.get("length", 15)
        return "".join(random.choices(_LETTERS, k=length))

    elif ctype == "composite":
        pattern: str = col["pattern"]
        # Replace {colname} references with already-generated values in this row
        result = pattern
        for ref_name, ref_val in prev_values.items():
            result = result.replace(f"{{{ref_name}}}", ref_val)
        return result

    elif ctype == "random_float":
        lo = col.get("min", 0.0)
        hi = col.get("max", 100.0)
        return f"{random.uniform(lo, hi):.2f}"

    elif ctype == "random_timestamp":
        days_back = col.get("days_back", 365)
        ts = datetime.now() - timedelta(days=random.randint(0, days_back))
        return ts.strftime("%Y-%m-%d %H:%M:%S")

    else:
        raise ValueError(f"Unknown column type '{ctype}' in config.yaml")


def generate_test_data(file_path: str, num_rows: int, columns: list[dict]):
    """
    Generate a headerless CSV file using the column definitions from config.yaml.
    Skips generation if the file already exists.
    """
    if os.path.exists(file_path):
        logger.info("File '%s' already exists, skipping generation.", file_path)
        return

    logger.info("Generating %d rows into '%s' ...", num_rows, file_path)
    start = time.time()

    batch_size = 50_000
    with open(file_path, "w", buffering=8 * 1024 * 1024) as fh:
        batch: list[str] = []
        for i in range(1, num_rows + 1):
            prev: dict[str, str] = {}
            fields: list[str] = []
            for col in columns:
                val = _generate_value(col, i, prev)
                prev[col["name"]] = val
                fields.append(val)
            batch.append(",".join(fields) + "\n")
            if i % batch_size == 0:
                fh.writelines(batch)
                batch.clear()
        if batch:
            fh.writelines(batch)

    logger.info("Generated %d rows in %.2f s.", num_rows, time.time() - start)
