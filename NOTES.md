Searched for "vmodule"
Searched for "tablet_service"

YugabyteDB 並沒有一個單一的「Debug 開關」（一鍵啟動的 Debug 模式），但它擁有**非常強大且細緻的日誌輸出（Logging）與追蹤機制**。因為它是分散式資料庫，分為上層的 PostgreSQL (YSQL) 引擎與下層的 C++ 儲存引擎 (DocDB)，你可以透過調整兩邊的參數，完整觀察一筆 `INSERT` 指令從客戶端進入，直到落實為實體檔案的整段生命週期。

要觀察你所描述的完整 INSERT 過程，你需要結合 **PostgreSQL 的日誌設定** 與 **DocDB 的模組化日誌 (`vmodule`)**。

以下是觀察一筆 `INSERT` 完整歷程的方法以及它會經過的模組：

### 1. 階段一：接觸到 YSQL 入口 (PostgreSQL 處理)
當客戶端連線並發出 `INSERT` 時，首先由 PostgreSQL 的 Backend 行程接手（進行解析、規劃與執行）。
*   **如何觀察：** 設定 YSQL (Postgres) 的配置參數，將日誌等級調到最細。
*   **參數：** `log_statement='all'`, `log_min_messages='DEBUG5'` (或 DEBUG1~DEBUG5)
*   **結果：** 你會在 `postgresql.log` 中看到連線建立、`INSERT` 語法被解析 (Parser)、產生執行計畫 (Planner)、並進入執行器 (Executor)。

### 2. 階段二：YSQL 轉換請求並傳給 DocDB
PostgreSQL 執行器無法直接寫入硬碟，它會透過 RPC 將寫入的任務請求（如 `PgUpdate` 操作）發送給下層的 Tablet Server (TServer) Leader。
*   **如何觀察：** 開啟 YSQL 與 DocDB 溝通介面的 `vmodule` 日誌。
*   **參數 (`vmodule`)：** `pg_doc_op=2`, `pg_client=2`
*   **結果：** 日誌會顯示 Postgres 如何將 SQL 轉化為 YugabyteDB 專屬的 Key-Value (DocDB) 結構，並發出網路 RPC 呼叫。

### 3. 階段三：Leader 節點接收與啟動 Raft 共識機制
TServer 收到 RPC 寫入請求，找出對應的 Tablet Leader，並啟動 Raft 流程。
*   **如何觀察：** 追蹤 Tablet 服務與寫入操作。
*   **參數 (`vmodule`)：** `tablet_service=2`, `write_operation=2`
*   **結果：** 你會看到 Leader 節點分配一個時間戳記 (Hybrid Time)，並將該操作打包成一個 Write Operation。

### 4. 階段四：寫入 WAL (Write-Ahead Log) 與同步 Follower
Leader 必須確保資料安全，因此它會先將資料寫入自己的本機預寫日誌 (WAL)，同時平行透過網路發送 `UpdateConsensus` (AppendEntries) RPC 給其他 Follower 節點。
*   **如何觀察：** 追蹤 Raft 共識模組與 日誌模組。
*   **參數 (`vmodule`)：** `raft_consensus=2`, `log=2`, `peer=2`
*   **結果：** 這裡最精彩。你會看到 Leader 記錄 "Appending to Raft Log" (寫入 WAL)，然後看到 "Sending UpdateConsensus" 給 Follower。同時如果你查看 Follower 節點的日誌，會看到它們收到這筆資料並回覆 "ACK" 給 Leader。

### 5. 階段五：達成多數決並記錄到 Memory (MemTable) 中
當 Leader 收到過半數 (Majority) Follower 的 ACK 後，這筆交易就會被標記為 **Committed (已提交)**，並且立即套用到 Leader 與 Follower 的記憶體結構 (RocksDB / MemTable) 中。此時，客戶端會收到寫入成功的訊息。
*   **如何觀察：** 追蹤 Tablet 核心模組。
*   **參數 (`vmodule`)：** `tablet=2`, `docdb=2`
*   **結果：** 你會看到 "Applying operation" 以及資料正式以 Key-Value 形式進入 MemTable。

### 6. 階段六：背景從 MemTable Flush 寫入到底層 SSTable (硬碟)
資料不會一直留在記憶體。當 MemTable 滿了或經過一定時間，系統會在背景產生 Flush 操作，將資料壓縮並轉換成不可變的 SST 檔案存在檔案系統。
*   **如何觀察：** 追蹤 Flush 和整理機制。
*   **參數 (`vmodule`)：** `flush=2`, `memtable=1`, `db_impl=1`
*   **結果：** 日誌會提示 "Flushing MemTable to SSTable"，這通常是在 `INSERT` 發生一段時間之後非同步進行的。

---

### 如何在本地實戰測試？

如果你本機有編譯好的源碼，或者你想用 `yb-ctl` 在本機啟動一個叢集觀察這個現象，你可以使用以下指令一次性把這些「Debug 模式」全開（這會產生海量的日誌，建議只在測試一筆 INSERT 時使用）：

```bash
./bin/yb-ctl create --rf 3 \
  --tserver_flags="vmodule=tablet_service=2,pg_doc_op=2,raft_consensus=2,log=2,write_operation=2,tablet=2,flush=1" \
  --ysql_pg_conf_csv="log_statement='all',log_min_messages='DEBUG5'"
```

**補充說明 (`vmodule` 的用法)：**
YugabyteDB 底層使用 Google 的 glog。`vmodule=檔名=等級` 代表針對特定的 `.cc` 程式模組開啟詳細的追蹤。等級 `1` 是普通詳細，`2` 到 `3` 是非常底層的詳細資訊（有些甚至是 `4`）。

透過查看各節點 (Master, TServer) 在 `~/yugabyte-data/node-*/disk-1/yb-data/tserver/logs/` 下的 `.INFO` 與 PostgreSQL 的日誌，你就能將這整個 `INSERT` 生命週期像拼圖一樣無縫拼湊出來。

---

Searched for "set_vmodule"
Searched for "tserver_flags"

在 Kubernetes 環境中，因為叢集具有動態性（Pod 會被重新調度，日誌存在儲存卷或送到 stdout），要記錄並觀察這個過程，我們需要在部署配置上做調整，並搭配 Kubernetes 的工具或 Python 腳本來撈取日誌。

以下是在 K8s 環境的操作方式以及 Python 客戶端實作的思路：

### 一、 如何在 K8s 啟動這套「Debug 模式」

在 Kubernetes 中，YugabyteDB 通常透過 Helm Chart 來部署。你可以在 `values.yaml` 中透過給定 TServer flags 來套用這些設定。

**Helm `values.yaml` 範例：**
```yaml
tserver:
  tserverFlags:
    vmodule: "tablet_service=2,pg_doc_op=2,raft_consensus=2,log=2,write_operation=2,tablet=2,flush=1"
    ysql_pg_conf_csv: "log_statement='all',log_min_messages='DEBUG5'"
```
> **⚠️ 嚴重警告**：在 K8s 中全開這些參數會導致極大的磁碟 I/O，日誌檔案 (`yb-tserver.INFO` 與 `postgresql.log`) 會暴增。請**絕對不要**在生產環境 (Production) 或有正常流量的叢集中開啟。

#### 更進階：動態開關（免重啟 Pod）
為了避免不必要的大量日誌，如果是已經在運行的 K8s 叢集，最好的方式是連進 Pod 中，利用 `yb-ts-cli` **動態切換旗標**。這樣可以在你準備執行 Python 腳本的前一秒再開啟：
```bash
# 連進某個 tserver pod
kubectl exec -it yb-tserver-0 -n yb-demo -- bash

# 動態開啟 vmodule (不需重啟 tserver)
yb-ts-cli --server_address=yb-tserver-0.yb-tservers.yb-demo.svc.cluster.local:9100 \
  set_flag vmodule "tablet_service=2,pg_doc_op=2,raft_consensus=2,log=2,write_operation=2,tablet=2"

# 動態改變 PostgreSQL 配置 (需要 yb-ctl 或修改設定檔後 reload)
```

---

### 二、 可否用 Python 實作並記錄過程？

**答案是：可以，但不單純只是「資料庫連線腳本」。**

標準的資料庫驅動程式 (如 Python 的 `psycopg2` 或 `asyncpg`) 跑在 PostgreSQL 通訊協定上，**它們只能送出 `INSERT` 並得到「成功/失敗」的回覆**，無法從這個連線中自動拉取到底層 Raft consensus 的日誌。

若要用 Python 自動化記錄整個過程，你的 Python 腳本必須具備**雙重身分**：
1. **DB Client**：負責執行 SQL `INSERT`。
2. **K8s Log Aggregator**：負責透過 kubernetes API 去抓取三個 tserver Pod 在執行那瞬間的底層 Log。

#### Python 實作概念架構腳本

這需要安裝 `psycopg2-binary` 以及 `kubernetes` python 套件。

```python
import psycopg2
import time
from kubernetes import client, config
from datetime import datetime, timezone

def collect_k8s_logs(namespace, pod_prefix, start_time):
    """透過 K8s API 抓取從 start_time 開始的所有 tserver 日誌"""
    config.load_kube_config() # 讀取本地 ~/.kube/config
    v1 = client.CoreV1Api()
    
    pods = v1.list_namespaced_pod(namespace)
    tserver_pods = [p.metadata.name for p in pods.items if pod_prefix in p.metadata.name]
    
    logs = {}
    for pod in tserver_pods:
        # 抓取 YB-TServer 容器內的 stdout 日誌 (前提是你的 Helm 設定讓 log 輸出到 stdout)
        # 如果 log 在 /mnt/disk0 的檔案內，則需改用 v1.connect_get_namespaced_pod_exec 去下 cat 指令
        try:
            pod_log = v1.read_namespaced_pod_log(
                name=pod, 
                namespace=namespace, 
                container="yb-tserver",
                since_seconds=10 # 抓取過去 10 秒
            )
            logs[pod] = pod_log
        except Exception as e:
            logs[pod] = str(e)
            
    return logs

def main():
    # 1. 記錄開始時間
    start_time = datetime.now(timezone.utc)
    print(f"[*] 準備執行 INSERT, 時間: {start_time}")
    
    # 2. 透過 PostgreSQL 協定執行寫入
    conn = psycopg2.connect(
        host="<yb-tserver-IP-或-Service>", 
        port=5433, 
        database="yugabyte", 
        user="yugabyte", 
        password="password"
    )
    cur = conn.cursor()
    
    # 執行一組明顯的資料，方便在海量 Log 中 grep 搜尋
    trace_id = f"trace_test_{int(time.time())}"
    print(f"[*] 執行 INSERT, 追蹤 ID: {trace_id}")
    cur.execute(f"INSERT INTO test_table (id, val) VALUES (1, '{trace_id}')")
    conn.commit()
    cur.close()
    conn.close()
    print("[*] INSERT 指令完成，等待背後非同步機制 (Flush) 運作...")
    
    # 等待 2~3 秒讓 Raft sync 和 log 寫入完成
    time.sleep(3)
    
    # 3. 觸發 K8s API 搜集 TServer 節點日誌
    print("[*] 開始從 Kubernetes 收集 3 個 TServer 節點的底層日誌...")
    logs = collect_k8s_logs(namespace="yb-demo", pod_prefix="yb-tserver", start_time=start_time)
    
    # 4. 分析並記錄
    with open("yugabyte_insert_trace.log", "w") as f:
        f.write(f"=== YB INSERT TRACE [{trace_id}] ===\n")
        # 這裡由於原始 log 會很多，實作上通常會用 re (RegEx) 去 grep `raft` / `tablet_service` / `pg_doc_op` 關鍵字
        for pod, log_content in logs.items():
            f.write(f"\n--- POD: {pod} ---\n")
            # 實務上可用迴圈過濾只含有 trace_id 或是相關模組的訊息
            for line in log_content.split('\n'):
                if "raft" in line.lower() or "tablet" in line.lower() or trace_id in line:
                     f.write(line + "\n")

    print("[*] 日誌已儲存至 yugabyte_insert_trace.log，你可以從中觀察 Consensus 過程。")

if __name__ == "__main__":
    main()
```

### 總結
1. **設定面：** Kubernetes 中可透過修改 deployment argument 或 Helm `values.yaml` 給予 `tserver_flags`。
2. **實作面：** Python 無法單純依靠 SQL 連線知道底層資訊。必須將 Python 製作成一個**打 SQL 後轉身去 K8s API (或 Elasticsearch / Loki 等 Log Collector) 撈取 TServer 系統日誌**的自動化腳本，再利用特有的欄位值 (如 `trace_test_xxx`) 作為字串比對，把跨 3 個 Node 的行為軌跡串合起來。