import yaml
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load and parse the YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    logger.info("Configuration loaded from '%s'", config_path)
    return cfg


def get_connection_string(cfg: dict) -> str:
    """Assemble a psycopg2 DSN from the structured database block in config.yaml."""
    db = cfg["database"]
    dsn = (
        f"host={db['host']} "
        f"port={db['port']} "
        f"dbname={db['dbname']} "
        f"user={db['user']} "
        f"password={db['password']}"
    )
    if options := db.get("options"):
        dsn += f" options='{options}'"
    return dsn


def get_write_copy_sql(cfg: dict) -> str:
    """Extract the COPY SQL for write benchmarks."""
    return cfg["queries"]["write"]["copy_sql"]


def get_read_query(cfg: dict, mode: str) -> tuple[str, list[dict]]:
    """
    Extract the SQL and parameter spec for a read query mode.

    Args:
        cfg: Loaded configuration dictionary.
        mode: One of 'read_standard' or 'read_optimized'.

    Returns:
        (sql_string, parameters_spec_list)
    """
    query_cfg = cfg["queries"][mode]
    return query_cfg["sql"], query_cfg.get("parameters", [])


def generate_query_params(parameters_spec: list[dict]) -> tuple:
    """
    Generate a concrete parameter tuple from the parameter spec list.

    Supports:
        - type: 'float_range'  -> generates (lo, hi) float pair
    """
    values = []
    for spec in parameters_spec:
        ptype = spec["type"]
        if ptype == "float_range":
            lo = random.uniform(spec["min"], spec["max"])
            hi = lo + random.uniform(spec["range_size_min"], spec["range_size_max"])
            values.extend([lo, hi])
        else:
            raise ValueError(f"Unknown parameter type: '{ptype}' in config.yaml")
    return tuple(values)


def get_schema_tables(cfg: dict) -> dict:
    """Return the tables dict from the schema block."""
    return cfg["schema"]["tables"]


def get_data_generation_columns(cfg: dict) -> list[dict]:
    """Return the column spec list for the data generator."""
    return cfg["data_generation"]["columns"]
