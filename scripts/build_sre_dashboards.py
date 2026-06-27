#!/usr/bin/env python3
"""Generate focused YugabyteDB SRE Grafana dashboards."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = ROOT / "config" / "grafana" / "dashboards"

PROM = {"type": "prometheus", "uid": "prometheus"}
YSQL = {"type": "postgres", "uid": "ysql"}


def target_prom(ref_id: str, expr: str, legend: str = "") -> dict:
    return {
        "datasource": PROM,
        "expr": expr,
        "legendFormat": legend,
        "refId": ref_id,
    }


def target_sql(ref_id: str, sql: str) -> dict:
    return {
        "datasource": YSQL,
        "format": "table",
        "rawQuery": True,
        "rawSql": sql.strip(),
        "refId": ref_id,
    }


def panel(
    panel_id: int,
    title: str,
    panel_type: str,
    x: int,
    y: int,
    w: int,
    h: int,
    targets: list[dict],
    description: str = "",
) -> dict:
    return {
        "id": panel_id,
        "title": title,
        "type": panel_type,
        "datasource": targets[0]["datasource"] if targets else PROM,
        "description": description,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {
            "defaults": {
                "custom": {},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "orange", "value": 1},
                        {"color": "red", "value": 5},
                    ],
                },
            },
            "overrides": [],
        },
        "options": {
            "legend": {"displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "none"},
        },
    }


def dashboard(uid: str, title: str, tags: list[str], panels: list[dict]) -> dict:
    return {
        "uid": uid,
        "title": title,
        "tags": ["YugabyteDB", "SRE", *tags],
        "timezone": "utc",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "5s",
        "editable": True,
        "graphTooltip": 0,
        "time": {"from": "now-30m", "to": "now"},
        "templating": {
            "list": [
                {
                    "name": "dbcluster",
                    "type": "query",
                    "datasource": PROM,
                    "query": "label_values(node_prefix)",
                    "label": "YugabyteDB Cluster",
                    "refresh": 1,
                    "includeAll": False,
                    "multi": False,
                }
            ]
        },
        "annotations": {"list": []},
        "panels": panels,
    }


def service_health_dashboard() -> dict:
    return dashboard(
        "yb-sre-service-health",
        "YugabyteDB SRE - Service Health",
        ["service-health", "prometheus"],
        [
            panel(
                1,
                "Master Nodes Up",
                "stat",
                0,
                0,
                6,
                4,
                [target_prom("A", 'sum(up{node_prefix="$dbcluster", export_type="master_export"})')],
            ),
            panel(
                2,
                "TServer Nodes Up",
                "stat",
                6,
                0,
                6,
                4,
                [target_prom("A", 'sum(up{node_prefix="$dbcluster", export_type="tserver_export"})')],
            ),
            panel(
                3,
                "YSQL Ops/sec",
                "timeseries",
                12,
                0,
                12,
                8,
                [
                    target_prom(
                        "A",
                        'sum(irate(rpc_latency_count{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_SelectStmt_count"}[5m]))',
                        "select",
                    ),
                    target_prom(
                        "B",
                        'sum(irate(rpc_latency_count{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_InsertStmt_count"}[5m]))',
                        "insert",
                    ),
                    target_prom(
                        "C",
                        'sum(irate(rpc_latency_count{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_UpdateStmt_count"}[5m]))',
                        "update",
                    ),
                    target_prom(
                        "D",
                        'sum(irate(rpc_latency_count{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_DeleteStmt_count"}[5m]))',
                        "delete",
                    ),
                ],
            ),
            panel(
                4,
                "YSQL Avg Latency",
                "timeseries",
                0,
                4,
                12,
                8,
                [
                    target_prom(
                        "A",
                        'sum(irate(rpc_latency_sum{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_SelectStmt_sum"}[5m])) / sum(irate(rpc_latency_count{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_SelectStmt_count"}[5m]))',
                        "select avg",
                    ),
                    target_prom(
                        "B",
                        'sum(irate(rpc_latency_sum{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_InsertStmt_sum"}[5m])) / sum(irate(rpc_latency_count{node_prefix="$dbcluster",saved_name="handler_latency_yb_ysqlserver_SQLProcessor_InsertStmt_count"}[5m]))',
                        "insert avg",
                    ),
                ],
            ),
            panel(
                5,
                "RPC Queue Pressure",
                "timeseries",
                0,
                12,
                12,
                8,
                [
                    target_prom("A", 'max(rpcs_in_queue_yb_tserver_TabletServerService{node_prefix="$dbcluster",export_type="tserver_export"})', "tserver"),
                    target_prom("B", 'max(rpcs_in_queue_yb_master_MasterService{node_prefix="$dbcluster"})', "master"),
                    target_prom("C", 'max(rpcs_in_queue_yb_ysqlserver_SQLServerService{node_prefix="$dbcluster"})', "ysql"),
                ],
            ),
            panel(
                6,
                "Log Warnings and Errors",
                "timeseries",
                12,
                12,
                12,
                8,
                [
                    target_prom("A", 'sum(rate(glog_warning_messages{node_prefix="$dbcluster"}[5m]))', "warnings/sec"),
                    target_prom("B", 'sum(rate(glog_error_messages{node_prefix="$dbcluster"}[5m]))', "errors/sec"),
                ],
            ),
            panel(
                7,
                "Memory Allocated by Node",
                "timeseries",
                0,
                20,
                12,
                8,
                [target_prom("A", 'avg by (exported_instance) (generic_current_allocated_bytes{node_prefix="$dbcluster"}) / 1048576', "{{exported_instance}}")],
            ),
            panel(
                8,
                "Reactor Delays",
                "timeseries",
                12,
                20,
                12,
                8,
                [
                    target_prom(
                        "A",
                        'avg by (exported_instance) (irate(handler_latency_yb_tserver_TabletServerService_Read_sum{node_prefix="$dbcluster"}[5m]) / irate(handler_latency_yb_tserver_TabletServerService_Read_count{node_prefix="$dbcluster"}[5m]))',
                        "{{exported_instance}} read",
                    )
                ],
            ),
        ],
    )


def query_insights_dashboard() -> dict:
    return dashboard(
        "yb-sre-query-insights",
        "YugabyteDB SRE - Query Insights",
        ["queries", "ysql"],
        [
            panel(
                1,
                "Live Active Queries",
                "table",
                0,
                0,
                24,
                8,
                [
                    target_sql(
                        "A",
                        """
                        SELECT datname, usename, state, client_addr::text AS client_addr,
                               now() - query_start AS elapsed, wait_event_type, wait_event,
                               left(query, 500) AS query
                        FROM pg_stat_activity
                        WHERE pid <> pg_backend_pid()
                          AND state <> 'idle'
                        ORDER BY query_start NULLS LAST
                        LIMIT 50;
                        """,
                    )
                ],
            ),
            panel(
                2,
                "Long Running Sessions",
                "table",
                0,
                8,
                12,
                8,
                [
                    target_sql(
                        "A",
                        """
                        SELECT datname, usename, state, client_addr::text AS client_addr,
                               now() - query_start AS elapsed, left(query, 500) AS query
                        FROM pg_stat_activity
                        WHERE query_start IS NOT NULL
                          AND now() - query_start > interval '5 seconds'
                        ORDER BY elapsed DESC
                        LIMIT 50;
                        """,
                    )
                ],
            ),
            panel(
                3,
                "Waiting or Blocked Sessions",
                "table",
                12,
                8,
                12,
                8,
                [
                    target_sql(
                        "A",
                        """
                        SELECT datname, usename, state, wait_event_type, wait_event,
                               now() - query_start AS elapsed, left(query, 500) AS query
                        FROM pg_stat_activity
                        WHERE wait_event IS NOT NULL
                           OR wait_event_type IS NOT NULL
                        ORDER BY elapsed DESC NULLS LAST
                        LIMIT 50;
                        """,
                    )
                ],
            ),
            panel(
                4,
                "Slow Statements by Mean Time",
                "table",
                0,
                16,
                12,
                9,
                [
                    target_sql(
                        "A",
                        """
                        SELECT r.rolname AS user_name, calls,
                               round(total_time::numeric, 2) AS total_time_ms,
                               round(mean_time::numeric, 2) AS mean_time_ms,
                               rows, left(query, 500) AS query
                        FROM pg_stat_statements s
                        JOIN pg_roles r ON r.oid = s.userid
                        ORDER BY mean_time DESC
                        LIMIT 20;
                        """,
                    )
                ],
            ),
            panel(
                5,
                "High Frequency Statements",
                "table",
                12,
                16,
                12,
                9,
                [
                    target_sql(
                        "A",
                        """
                        SELECT r.rolname AS user_name, calls,
                               round(total_time::numeric, 2) AS total_time_ms,
                               round(mean_time::numeric, 2) AS mean_time_ms,
                               rows, left(query, 500) AS query
                        FROM pg_stat_statements s
                        JOIN pg_roles r ON r.oid = s.userid
                        ORDER BY calls DESC
                        LIMIT 20;
                        """,
                    )
                ],
            ),
            panel(
                6,
                "Recently Terminated Queries",
                "table",
                0,
                25,
                24,
                8,
                [
                    target_sql(
                        "A",
                        """
                        SELECT databasename, backend_pid, termination_reason,
                               query_start_time, query_end_time,
                               left(query_text, 500) AS query_text
                        FROM yb_terminated_queries
                        ORDER BY query_end_time DESC
                        LIMIT 50;
                        """,
                    )
                ],
            ),
        ],
    )


def hotspots_dashboard() -> dict:
    return dashboard(
        "yb-sre-hotspots",
        "YugabyteDB SRE - Hotspots",
        ["hotspots", "prometheus", "ysql"],
        [
            panel(
                1,
                "Top Tables by Read Ops",
                "table",
                0,
                0,
                12,
                8,
                [
                    target_prom(
                        "A",
                        'topk(10, sum by (table_name) (irate(rpc_latency_count{node_prefix="$dbcluster",export_type="tserver_export",saved_name="handler_latency_yb_tserver_TabletServerService_Read_count",table_name!=""}[5m])))',
                        "{{table_name}}",
                    )
                ],
            ),
            panel(
                2,
                "Top Tables by Write Ops",
                "table",
                12,
                0,
                12,
                8,
                [
                    target_prom(
                        "A",
                        'topk(10, sum by (table_name) (irate(rpc_latency_count{node_prefix="$dbcluster",export_type="tserver_export",saved_name="handler_latency_yb_tserver_TabletServerService_Write_count",table_name!=""}[5m])))',
                        "{{table_name}}",
                    )
                ],
            ),
            panel(
                3,
                "Node Read/Write Pressure",
                "timeseries",
                0,
                8,
                24,
                8,
                [
                    target_prom(
                        "A",
                        'sum by (exported_instance) (irate(rpc_latency_count{node_prefix="$dbcluster",export_type="tserver_export",saved_name="handler_latency_yb_tserver_TabletServerService_Read_count"}[5m]))',
                        "{{exported_instance}} read",
                    ),
                    target_prom(
                        "B",
                        'sum by (exported_instance) (irate(rpc_latency_count{node_prefix="$dbcluster",export_type="tserver_export",saved_name="handler_latency_yb_tserver_TabletServerService_Write_count"}[5m]))',
                        "{{exported_instance}} write",
                    ),
                ],
            ),
            panel(
                4,
                "High Frequency DB Users",
                "table",
                0,
                16,
                12,
                8,
                [
                    target_sql(
                        "A",
                        """
                        SELECT r.rolname AS usename, sum(s.calls) AS calls,
                               round(sum(s.total_time)::numeric, 2) AS total_time_ms,
                               round((sum(s.total_time) / nullif(sum(s.calls), 0))::numeric, 2) AS avg_time_ms
                        FROM pg_stat_statements s
                        JOIN pg_roles r ON r.oid = s.userid
                        GROUP BY r.rolname
                        ORDER BY calls DESC
                        LIMIT 20;
                        """,
                    )
                ],
            ),
            panel(
                5,
                "Top Client Addresses",
                "table",
                12,
                16,
                12,
                8,
                [
                    target_sql(
                        "A",
                        """
                        SELECT client_addr::text AS client_addr, usename,
                               count(*) AS sessions,
                               count(*) FILTER (WHERE state = 'active') AS active_sessions
                        FROM pg_stat_activity
                        WHERE client_addr IS NOT NULL
                        GROUP BY client_addr, usename
                        ORDER BY sessions DESC, active_sessions DESC
                        LIMIT 20;
                        """,
                    )
                ],
            ),
            panel(
                6,
                "Table Storage Footprint",
                "table",
                0,
                24,
                24,
                8,
                [
                    target_sql(
                        "A",
                        """
                        SELECT schemaname, relname AS table_name,
                               pg_size_pretty(pg_total_relation_size(format('%I.%I', schemaname, relname))) AS total_size,
                               pg_total_relation_size(format('%I.%I', schemaname, relname)) AS bytes
                        FROM pg_stat_user_tables
                        ORDER BY bytes DESC
                        LIMIT 20;
                        """,
                    )
                ],
            ),
        ],
    )


def main() -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    dashboards = {
        "yugabytedb-sre-service-health.json": service_health_dashboard(),
        "yugabytedb-sre-query-insights.json": query_insights_dashboard(),
        "yugabytedb-sre-hotspots.json": hotspots_dashboard(),
    }
    for filename, data in dashboards.items():
        (DASHBOARD_DIR / filename).write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
