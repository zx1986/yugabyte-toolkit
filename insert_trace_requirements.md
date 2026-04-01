# YugabyteDB 寫入路徑追蹤自動化需求 (Insert Trace Automation Requirements)

## 1. 背景與目標 (Background & Objective)
專案情境為深入研究與除錯 YugabyteDB 的寫入路徑（Write Path）。具體目標是觀察一筆 `INSERT` 語句從 PostgreSQL (YSQL) 引擎解析，轉換至底層 DocDB，經過 Raft 共識機制，最終落成實體檔案（SSTable）的完整生命週期。
為了在 Kubernetes 的動態環境中達成此目的，需要開發一套自動化工具，能觸發帶有追蹤標記的寫入操作，並同步收集各節點底層日誌，重組為清晰的操作軌跡。

## 2. 核心功能需求 (Core Requirements)

### 2.1 階段性日誌配置 (Log Configuration)
必須能夠動態或靜態設定以下日誌參數，以暴露完整的寫入軌跡：
*   **YSQL 端**：設定 `log_statement='all'`, `log_min_messages='DEBUG5'`。
*   **DocDB 端 (`vmodule`)**：需開啟包含 `tablet_service=2`, `pg_doc_op=2`, `raft_consensus=2`, `log=2`, `write_operation=2`, `tablet=2`, `flush=1` 等模組的追蹤。

### 2.2 自動化追蹤腳本 (Python Automation Script)
需開發一支兼具 **資料庫客戶端** 與 **K8s 日誌收集器** 雙重身分的 Python 腳本：
*   **請求標記 (Trace ID Injection)**：執行 `INSERT` 時，帶入唯一時間戳記或 UUID（如 `trace_id`），以便作為搜尋錨點。
*   **自動化 K8s 日誌抓取**：利用 Kubernetes Python Client，在 SQL 執行完成並等待適當時間（考量非同步與 Flush 延遲）後，自動抓取目標 Replica (TServer Pods) 的 stdout 日誌。

### 2.3 日誌過濾與重組分析 (Log Filtering & Tracing)
*   **去蕪存菁**：將抓取到的多節點原始日誌進行分析，利用正規表達式或關鍵字（Trace ID 以及核心模組關鍵字如 `raft`, `tablet`）過濾。
*   **軌跡輸出**：最終將所有節點整理好的日誌，統一輸出成一份具時序性、便於閱讀的追蹤報告文件。

## 3. 非功能性需求與約束 (Non-Functional Requirements & Constraints)
*   **系統效能防護**：全開 Debug 日誌會產生巨量 I/O。腳本應實作防護機制，例如操作完成後立刻關閉 Debug 模式，且**嚴禁**在生產環境 (Production) 執行。
*   **免重啟設計 (Hot-Reload)**：針對 K8s 叢集，應優先考量使用 `yb-ts-cli set_flag` 進行動態參數變更，減少 Pod 重啟對觀察環境的干擾。
