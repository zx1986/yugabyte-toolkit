# Design Specification: Local YugabyteDB Metrics Collector and SRE Grafana Dashboard

This document outlines the design and configuration for collecting local YugabyteDB metrics and setting up an official baseline Grafana dashboard using Prometheus and Grafana via Docker Compose Profiles.

---

## 1. Context and Goals

### Context
The current repository contains a local 3-node YugabyteDB cluster managed by Docker Compose (`yb-node1`, `yb-node2`, `yb-node3`).

### Goals
- Design and integrate a local metrics collection stack (Prometheus + Grafana).
- Scraping YugabyteDB nodes' native metrics at **1-second intervals** for high-resolution benchmark monitoring.
- Configure automatic data sources and dashboards provisioning so that the stack is fully configured on startup.
- Use the official YugabyteDB Grafana Dashboard (`YugabyteDB.json`) as the basic, untouchable dashboard, laying groundwork for future customized SRE dashboards.
- Use **Docker Compose Profiles** (`metrics`) to ensure metrics components do not consume resources unless explicitly enabled.

---

## 2. Metrics Scraping Architecture

### Scrape Ports and Endpoints
In the 3-node local `yugabyted` cluster, each node runs both Master and TServer services:
- **Master UI/Metrics Endpoint**: Exposed on port `7000` via `/prometheus-metrics`.
- **TServer UI/Metrics Endpoint**: Exposed on port `9000` via `/prometheus-metrics`.
- **YCQL Metrics Endpoint**: Exposed on port `12000` via `/prometheus-metrics`.
- **YSQL Metrics Endpoint**: Exposed on port `13000` via `/prometheus-metrics`.
- **YEDIS Metrics Endpoint**: Exposed on port `11000` via `/prometheus-metrics`.

All nodes are connected to the bridge network `yb-net`. The Prometheus container will scrape these node endpoints using container hostnames (e.g., `yb-node1:9000`, `yb-node2:7000`, etc.).

---

## 3. Prometheus Configuration (`config/prometheus/prometheus.yml`)

We configure the scrape interval to **1s** and implement target relabeling based on YugabyteDB's official configuration. This relabeling converts `handler_latency_*` metrics into standard `rpc_latency` metrics with labels (e.g. `service_method`, `service_type`), which are required by the official dashboard.

```yaml
global:
  scrape_interval: 1s
  evaluation_interval: 1s

scrape_configs:
  - job_name: "yugabytedb-local"
    metrics_path: /prometheus-metrics
    relabel_configs:
      - target_label: "node_prefix"
        replacement: "local-ycpg" # Identifies this local cluster

    metric_relabel_configs:
      # 1. Save original metric name
      - source_labels: ["__name__"]
        regex: "(.*)"
        target_label: "saved_name"
        replacement: "$1"
      
      # 2. Extract server_type (e.g., yb_tserver or yb_master)
      - source_labels: ["__name__"]
        regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(.*)"
        target_label: "server_type"
        replacement: "$1"
      
      # 3. Extract service_type (e.g., TabletServerService or MasterService)
      - source_labels: ["__name__"]
        regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(.*)"
        target_label: "service_type"
        replacement: "$2"
      
      # 4. Extract service_method (e.g., Read or Write)
      - source_labels: ["__name__"]
        regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(_sum|_count)?"
        target_label: "service_method"
        replacement: "$3"
      
      # 5. Rename to rpc_latency_sum / rpc_latency_count
      - source_labels: ["__name__"]
        regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(_sum|_count)?"
        target_label: "__name__"
        replacement: "rpc_latency$4"

    static_configs:
      # Master Nodes
      - targets: ["yb-node1:7000", "yb-node2:7000", "yb-node3:7000"]
        labels:
          group: "yb-master"
          export_type: "master_export"

      # TServer Base
      - targets: ["yb-node1:9000", "yb-node2:9000", "yb-node3:9000"]
        labels:
          group: "yb-tserver"
          export_type: "tserver_export"

      # YCQL Metrics
      - targets: ["yb-node1:12000", "yb-node2:12000", "yb-node3:12000"]
        labels:
          group: "ycql"
          export_type: "cql_export"

      # YSQL Metrics
      - targets: ["yb-node1:13000", "yb-node2:13000", "yb-node3:13000"]
        labels:
          group: "ysql"
          export_type: "ysql_export"

      # YEDIS Metrics
      - targets: ["yb-node1:11000", "yb-node2:11000", "yb-node3:11000"]
        labels:
          group: "yedis"
          export_type: "redis_export"
```

---

## 4. Grafana Provisioning Configuration

To automatically provision Prometheus datasource and dashboards without manual steps:

### A. Datasources Provisioning (`config/grafana/provisioning/datasources/prometheus.yml`)
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://yb-prometheus:9090
    isDefault: true
    editable: true
```

### B. Dashboards Provisioning (`config/grafana/provisioning/dashboards/dashboards.yml`)
```yaml
apiVersion: 1

providers:
  - name: 'YugabyteDB Dashboards'
    orgId: 1
    folder: 'YugabyteDB'
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
```

### C. Base Dashboard
Download and save the official YugabyteDB dashboard JSON file from [YugabyteDB.json](https://raw.githubusercontent.com/yugabyte/yugabyte-db/master/cloud/grafana/YugabyteDB.json) into `config/grafana/dashboards/yugabytedb-official.json`.

---

## 5. Docker Compose and Service Profiles (`docker-compose.yaml`)

Add `prometheus` and `grafana` services mapped under the `metrics` profile to prevent automatic startup during baseline testing.

```yaml
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: yb-prometheus
    profiles:
      - metrics
    volumes:
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - yb_prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
    networks:
      - yb-net
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.4.1
    container_name: yb-grafana
    profiles:
      - metrics
    ports:
      - "3000:3000"
    volumes:
      - ./config/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./config/grafana/dashboards:/var/lib/grafana/dashboards:ro
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - yb-net
    depends_on:
      - prometheus

volumes:
  yb_prometheus_data:
```

---

## 6. Verification and Setup Instructions

1. **Start Cluster with Metrics Enabled**:
   ```bash
   docker compose --profile metrics up -d
   ```
2. **Access Interfaces**:
   - Prometheus: `http://localhost:9090`
   - Grafana: `http://localhost:3000` (Login: `admin` / `admin`)
3. **Verify Dashboard**:
   Open Grafana, navigate to the Dashboard list under the "YugabyteDB" folder, and view the imported "YugabyteDB" dashboard. Check that panel values update at 1-second intervals.
