# YugabyteDB Metrics & Dashboard Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up local metrics collection (Prometheus) and visualization (Grafana) for a 3-node YugabyteDB cluster using Docker Compose Profiles with automatic provisioning of the official dashboard.

**Architecture:** Extend the existing Docker Compose configuration with Prometheus and Grafana containers under a separate `metrics` profile. Configure Prometheus to scrape metrics at 1-second intervals from all YugabyteDB ports (7000, 9000, 11000, 12000, 13000) using YugabyteDB's official metric relabeling rules. Automatically provision Prometheus as the default Grafana datasource and the official YugabyteDB JSON dashboard.

**Tech Stack:** Docker Compose, Prometheus v2.51.0, Grafana v10.4.1

---

### Task 1: Initialize Configuration Directories and Create Prometheus Scrape Config

**Files:**
- Create: `config/prometheus/prometheus.yml`

- [ ] **Step 1: Create Prometheus configuration file**
  Create the file `config/prometheus/prometheus.yml` with the following configuration:
  ```yaml
  global:
    scrape_interval: 1s
    evaluation_interval: 1s

  scrape_configs:
    - job_name: "yugabytedb-local"
      metrics_path: /prometheus-metrics
      relabel_configs:
        - target_label: "node_prefix"
          replacement: "local-ycpg"

      metric_relabel_configs:
        - source_labels: ["__name__"]
          regex: "(.*)"
          target_label: "saved_name"
          replacement: "$1"
        - source_labels: ["__name__"]
          regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(.*)"
          target_label: "server_type"
          replacement: "$1"
        - source_labels: ["__name__"]
          regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(.*)"
          target_label: "service_type"
          replacement: "$2"
        - source_labels: ["__name__"]
          regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(_sum|_count)?"
          target_label: "service_method"
          replacement: "$3"
        - source_labels: ["__name__"]
          regex: "handler_latency_(yb_[^_]*)_([^_]*)_([^_]*)(_sum|_count)?"
          target_label: "__name__"
          replacement: "rpc_latency$4"

      static_configs:
        - targets: ["yb-node1:7000", "yb-node2:7000", "yb-node3:7000"]
          labels:
            group: "yb-master"
            export_type: "master_export"

        - targets: ["yb-node1:9000", "yb-node2:9000", "yb-node3:9000"]
          labels:
            group: "yb-tserver"
            export_type: "tserver_export"

        - targets: ["yb-node1:12000", "yb-node2:12000", "yb-node3:12000"]
          labels:
            group: "ycql"
            export_type: "cql_export"

        - targets: ["yb-node1:13000", "yb-node2:13000", "yb-node3:13000"]
          labels:
            group: "ysql"
            export_type: "ysql_export"

        - targets: ["yb-node1:11000", "yb-node2:11000", "yb-node3:11000"]
          labels:
            group: "yedis"
            export_type: "redis_export"
  ```

- [ ] **Step 2: Verify Prometheus config exists**
  Run: `cat config/prometheus/prometheus.yml`
  Expected: Content matches the configuration above.

- [ ] **Step 3: Commit**
  Run:
  ```bash
  git add config/prometheus/prometheus.yml
  git commit -m "feat: add prometheus scrape config with yugabytedb relabeling"
  ```

---

### Task 2: Configure Grafana Provisioning and Fetch Official Dashboard JSON

**Files:**
- Create: `config/grafana/provisioning/datasources/prometheus.yml`
- Create: `config/grafana/provisioning/dashboards/dashboards.yml`
- Create: `config/grafana/dashboards/yugabytedb-official.json`

- [ ] **Step 1: Create Grafana datasource configuration**
  Create the file `config/grafana/provisioning/datasources/prometheus.yml` with the following configuration:
  ```yaml
  apiVersion: 1

  datasources:
    - name: Prometheus
      type: prometheus
      access: proxy
      url: http://prometheus:9090
      isDefault: true
      editable: true
  ```

- [ ] **Step 2: Create Grafana dashboard provisioning config**
  Create the file `config/grafana/provisioning/dashboards/dashboards.yml` with the following configuration:
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

- [ ] **Step 3: Download the official YugabyteDB dashboard JSON**
  Run:
  ```bash
  mkdir -p config/grafana/dashboards
  curl -sSL https://raw.githubusercontent.com/yugabyte/yugabyte-db/master/cloud/grafana/YugabyteDB.json -o config/grafana/dashboards/yugabytedb-official.json
  ```

- [ ] **Step 4: Verify the dashboard JSON was successfully downloaded**
  Run: `grep -q "YugabyteDB" config/grafana/dashboards/yugabytedb-official.json && echo "Valid JSON"`
  Expected output: `Valid JSON`

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add config/grafana/
  git commit -m "feat: add grafana provisioning configs and yugabytedb official dashboard json"
  ```

---

### Task 3: Integrate Metrics Services into docker-compose.yaml

**Files:**
- Modify: `docker-compose.yaml`

- [ ] **Step 1: Append prometheus and grafana services**
  Edit `docker-compose.yaml`. At the end of the `services:` block, append the definitions for `prometheus` and `grafana`. Also declare the volumes `yb_prometheus_data` and `yb_grafana_data` under the root-level `volumes:` section.
  
  Locate the end of `services:` definition:
  ```yaml
      deploy:
        resources:
          limits:
            memory: 2G
  ```
  Insert below `yb-node3` service:
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
        - yb_grafana_data:/var/lib/grafana
        - ./config/grafana/dashboards:/var/lib/grafana/dashboards:ro
      environment:
        - GF_SECURITY_ADMIN_PASSWORD=admin
        - GF_USERS_ALLOW_SIGN_UP=false
      networks:
        - yb-net
      depends_on:
        - prometheus
  ```

  And add the Prometheus and Grafana persistent volumes at the bottom under `volumes:`:
  ```diff
   volumes:
     yb_data1:
     yb_data2:
     yb_data3:
  +  yb_prometheus_data:
  +  yb_grafana_data:
  ```

- [ ] **Step 2: Validate docker-compose config syntax**
  Run: `docker compose config`
  Expected: Prints the resolved docker-compose configuration yaml without syntax errors.

- [ ] **Step 3: Commit**
  Run:
  ```bash
  git add docker-compose.yaml
  git commit -m "feat: integrate prometheus and grafana services in docker compose using metrics profile"
  ```

---

### Task 4: Verify Stack Integration

**Files:**
- None (verification step)

- [ ] **Step 1: Spin up the YugabyteDB cluster with the metrics profile**
  Run: `docker compose --profile metrics up -d`
  Expected output: Docker Compose starts all YugabyteDB nodes AND `yb-prometheus`, `yb-grafana` containers.

- [ ] **Step 2: Verify all containers are running**
  Run: `docker compose ps`
  Expected output: `yb-node1`, `yb-node2`, `yb-node3`, `yb-prometheus`, `yb-grafana` are all listed as Up/running.

- [ ] **Step 3: Verify metrics scrape status**
  Run: `curl -s http://localhost:9090/api/v1/targets | grep -q '"status":"up"' && echo "Prometheus Scraping Success"`
  Expected output: `Prometheus Scraping Success`

- [ ] **Step 4: Stop and tear down metrics and cluster**
  Run: `docker compose --profile metrics down -v`
  Expected output: Stops and deletes all containers and metrics volumes.
