# YugabyteDB Insert Trace Automation Design

## 1. Goal (目標)
建立一支 Python 自動化腳本並將其封裝為 Kubernetes Job。該腳本會在叢集內部執行 YugabyteDB `INSERT` 寫入操作，並透過 Kubernetes API 即時串流（Stream）與過濾叢集中各台 TServer (Tablet Server) 的系統日誌。最終將結果獨立儲存至持久卷 (PVC) 中，作為重現資料庫寫入軌跡的端到端除錯工具。

## 2. Architecture (系統架構)
*   **部署模型 (Deployment Model)**：作為 Kubernetes `Job` 短期任務部署於同一叢集內。
*   **網路與權限 (Networking & RBAC)**：
    *   K8s API 認證：使用 `InClusterConfig` 自動讀取容器內的 ServiceAccount 憑證，並需要賦予該 ServiceAccount `pods/log` 等級的最低讀取權限。
    *   資料庫連線：透過 K8s 內建 DNS 解析直連 YugabyteDB 服務 (無須對外 expose port)。
*   **日誌儲存 (Persistence)**：掛載 PersistentVolumeClaim (PVC) 至 Job 容器內，將最終產生的追蹤報告 (Trace Report) 寫入該磁碟，利於任務結束後分析。

## 3. Core Components (核心組件)

### 3.1. Database Client (YSQL 寫入器)
*   使用 `psycopg2` (或 async 版本)。
*   執行目標 `INSERT` SQL，並於欄位預先注入全域唯一的 `trace_id` (如 Timestamp + UUID)。

### 3.2. Kubernetes Stream Aggregator (日誌串流與過濾器)
*   使用 Kubernetes Python Client (`kubernetes.client.CoreV1Api`)。
*   呼叫 `read_namespaced_pod_log` 且帶入引數 `stream=True`。
*   利用平行處理（`ThreadPoolExecutor` 或 `asyncio`），同時對目標的 3 個 `yb-tserver` Pod 建立獨立連線讀取流。
*   **過濾邏輯**：逐行讀取 stdout，檢查該行字串是否包含發送的 `trace_id`。
*   **零緩存寫入**：符合條件的日誌直接 `append` (\n) 寫入 PVC 指定的文件路徑，嚴格控制記憶體消耗，避免 OOM。

## 4. Workflow (執行流程)
1.  **啟動與初始化**：載入 Kube config、初始化 K8s Client 與 DB 連線，開啟 PVC 日誌檔預備寫入。
2.  **建立監聽**：啟動背景 Thread/Task，開始串流 TServer 日誌。
3.  **觸發寫入**：對 YugabyteDB 發送帶有 `trace_id` 的 `INSERT` 操作。
4.  **延遲等待**：休眠 5 ~ 10 秒，等待背景的非同步機制（如 Raft 同步或 MemTable Flush 日誌）落地並被 K8s 串流捕捉。
5.  **結束與歸檔**：中斷串流連線，關閉檔案與連線，印出成功訊息後結束程序。

## 5. Security & Constraints (安全性與約束)
*   **Read-Only 擷取 (不變更系統設定)**：腳本完全不干涉 YugabyteDB 的日誌配置（不去開啟 `vmodule` 開關）。初期先於預設的非 Debug 模式下實踐日誌配對與串留截取機制，確立穩定性再考慮後續外部調整。
*   **單一職責**：無須賦予 `pods/exec` 高階權限，確保安全性。

## 6. Testing Strategy (測試策略)
*   使用 `kubectl create -f job.yaml` 觸發執行。
*   待 Job State 變更為 Completed 後，使用其他容器（或掛載同一個 PVC）讀取該日誌檔案，驗證 `trace_id` 是否成功撈出預期的寫入日誌。
