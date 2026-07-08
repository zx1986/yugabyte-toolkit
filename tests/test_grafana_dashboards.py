import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "config" / "grafana" / "dashboards"
DATASOURCE_FILE = ROOT / "config" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"


def load_dashboard(name: str) -> dict:
    return json.loads((DASHBOARD_DIR / name).read_text())


def panel_titles(dashboard: dict) -> set[str]:
    return {panel["title"] for panel in dashboard["panels"]}


def panel_queries(dashboard: dict) -> str:
    queries: list[str] = []
    for panel in dashboard["panels"]:
        for target in panel.get("targets", []):
            query = target.get("expr") or target.get("rawSql") or ""
            queries.append(query)
    return "\n".join(queries)


def test_provisions_prometheus_and_ysql_datasources():
    config = yaml.safe_load(DATASOURCE_FILE.read_text())
    datasources = {item["name"]: item for item in config["datasources"]}

    assert datasources["Prometheus"]["type"] == "prometheus"
    assert datasources["Prometheus"]["url"] == "http://prometheus:9090"

    ysql = datasources["YSQL"]
    assert ysql["type"] == "postgres"
    assert ysql["url"] == "yb-node1:5433"
    assert ysql["database"] == "yugabyte"
    assert ysql["user"] == "yugabyte"
    assert ysql["jsonData"]["sslmode"] == "disable"


def test_sre_service_health_dashboard_uses_prometheus_service_signals():
    dashboard = load_dashboard("yugabytedb-sre-service-health.json")

    assert dashboard["title"] == "YugabyteDB SRE - Service Health"
    assert {
        "Master Nodes Up",
        "TServer Nodes Up",
        "YSQL Ops/sec",
        "YSQL Avg Latency",
        "RPC Queue Pressure",
        "Log Warnings and Errors",
    } <= panel_titles(dashboard)

    queries = panel_queries(dashboard)
    assert "up{node_prefix=\"$dbcluster\", export_type=\"master_export\"}" in queries
    assert "handler_latency_yb_ysqlserver_SQLProcessor_SelectStmt_count" in queries


def test_sre_query_insights_dashboard_uses_ysql_query_views():
    dashboard = load_dashboard("yugabytedb-sre-query-insights.json")

    assert dashboard["title"] == "YugabyteDB SRE - Query Insights"
    assert {
        "Live Active Queries",
        "Long Running Sessions",
        "Slow Statements by Mean Time",
        "High Frequency Statements",
        "Waiting or Blocked Sessions",
    } <= panel_titles(dashboard)

    queries = panel_queries(dashboard)
    assert "pg_stat_activity" in queries
    assert "pg_stat_statements" in queries
    assert "yb_terminated_queries" in queries


def test_sre_hotspots_dashboard_tracks_nodes_tables_and_accounts():
    dashboard = load_dashboard("yugabytedb-sre-hotspots.json")

    assert dashboard["title"] == "YugabyteDB SRE - Hotspots"
    assert {
        "Top Tables by Read Ops",
        "Top Tables by Write Ops",
        "Node Read/Write Pressure",
        "High Frequency DB Users",
        "Top Client Addresses",
    } <= panel_titles(dashboard)

    queries = panel_queries(dashboard)
    assert "table_name" in queries
    assert "exported_instance" in queries
    assert "usename" in queries
    assert "client_addr" in queries
