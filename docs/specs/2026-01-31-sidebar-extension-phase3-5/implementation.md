# 實作計畫

## 參考文件

**PRD 文件路徑：** `docs/specs/2026-01-31-sidebar-extension-phase3-5/prd.md`
**研究文件路徑：** `docs/research/2026-01-31-comfyui-sidebar-extension.md`

## 任務概要

- [x] 實作後端下載 API 與 WebSocket 進度推送
- [x] 擴展前端 ModelCard 下載狀態與進度 UI
- [x] 實作前端下載流程整合（單一下載、批次下載、取消）
- [x] 實作後端 Workflow 生成 API
- [x] 實作前端 Workflow 生成與 Canvas 載入
- [x] 研究 Workflow 節點自動排版方案
- [x] 實作 Workflow 節點自動排版
- [x] 發佈準備（GitHub Actions、版本號、README）
- [ ] 執行驗收測試
- [ ] 更新專案文件

## 任務細節

### 實作後端下載 API 與 WebSocket 進度推送

**實作要點**
- 在 `civitai_routes.py` 中新增三個 API endpoint（使用既有的裝飾器模式）：
  - `POST /civitai/download`：接受 `{ resource, api_key }`，啟動單一模型下載
    - 使用 `asyncio.create_task()` 在背景執行下載，立即回傳 `{ task_id }` 給前端
    - task_id 使用 uuid4 生成
  - `POST /civitai/download-all`：接受 `{ resources: [...], api_key }`，依序下載多個模型
    - 同樣使用 `asyncio.create_task()` 背景執行，回傳 `{ task_id }`
    - 內部依序呼叫單一下載邏輯（一次只下載一個）
  - `POST /civitai/download-cancel`：接受 `{ task_id }` 或 `{ cancel_all: true }`
    - 設定取消旗標，下載迴圈在下一個 chunk 檢查時中止
    - 刪除未完成的 `.part` 暫存檔案
- 建立下載核心邏輯（在 `civitai_routes.py` 中或新建 `civitai_download.py`）：
  - 使用 `aiohttp.ClientSession` 進行非同步 HTTP 下載（不使用同步的 `requests`，避免阻塞 event loop）
  - 下載目標路徑使用 `FolderPathsModelAdapter.get_model_dir()` 確定
  - 寫入時使用 `.part` 副檔名（例如 `model.safetensors.part`）
  - 每下載一個 chunk（建議 64KB），透過 WebSocket 推送進度事件
  - 下載完成後計算 SHA256 校驗（使用 `hashlib.sha256`），與 resource 中的 `hashes.SHA256` 比對
  - 校驗成功後 rename `.part` 檔案為正式檔名
  - 校驗失敗或取消時，刪除 `.part` 檔案
- 用模組層級 dict 追蹤進行中的下載任務：`_active_downloads: Dict[str, DownloadTask]`
  - `DownloadTask` 包含：task_id、asyncio.Task reference、cancel Event、resource info
- WebSocket 進度推送使用 `PromptServer.instance.send_sync()`：
  - 事件名稱：`civitai.download.progress`
  - payload：`{ task_id, filename, status, progress, downloaded_bytes, total_bytes, error }`
  - status 值：`downloading`、`verifying`、`completed`、`failed`、`cancelled`
  - 進度更新頻率：不超過每 500ms 一次（避免 WebSocket 過載）
- Civitai 下載 URL 需要 API key 認證：在 request header 加入 `Authorization: Bearer {api_key}` 或在 URL 加入 `?token={api_key}`
- 處理 Civitai 回傳的 Content-Disposition header（可能提供不同的檔名）

**相關檔案**
- `civitai_routes.py` — 新增 3 個 route handler + 下載核心邏輯
- `civitai_utils/model_manager.py` — 參考既有 `download_file()` 的實作方式（Content-Disposition 處理等）
- `pipeline/resolve_models.py` — 了解 resource dict 結構（download_url、target_path 等欄位）

**完成檢查**
- 啟動 ComfyUI 後，使用 curl 測試：
  - `POST /civitai/download` 回傳 `{ task_id: "..." }` 且不阻塞（立即回傳）
  - `POST /civitai/download-cancel` 可以取消進行中的下載
- 下載完成後，檔案出現在正確的 ComfyUI models 目錄中
- 取消下載後，`.part` 暫存檔案已被刪除
- WebSocket 訊息可以在 ComfyUI 的瀏覽器 console 中觀察到（`ws.onmessage` 事件）

**實作備註**
[後續依賴] resolve_models.py 的 `_fill_from_version_data()` 新增了 `result["hashes"] = primary_file.get("hashes")` 來保存 Civitai API 的 SHA256 hash，前端傳送 resource 到 download API 時須包含此欄位。

---

### 擴展前端 ModelCard 下載狀態與進度 UI

**實作要點**
- 擴展 `ui/src/types/index.ts` 中的 `Resource` 型別：
  - 新增 `downloadStatus?: 'idle' | 'downloading' | 'verifying' | 'completed' | 'failed' | 'cancelled'`
  - 新增 `downloadProgress?: number`（0-100 百分比）
  - 新增 `downloadedBytes?: number`
  - 新增 `totalBytes?: number`
  - 新增 `downloadError?: string`
  - 新增 `taskId?: string`
- 修改 `ui/src/components/ModelCard.vue`，支援 7 種視覺狀態：
  - **已存在**（`already_downloaded=true`）：✅ + 路徑（現有行為，不變）
  - **缺少且已解析**（`resolved=true, !already_downloaded`）：❌ + Download 按鈕
  - **缺少且未解析**（`!resolved`）：❌ + "Cannot resolve" 文字（現有行為，不變）
  - **下載中**（`downloadStatus='downloading'`）：⏳ + 進度條 + 百分比 + 已下載/總量 + Cancel 按鈕
  - **校驗中**（`downloadStatus='verifying'`）：⏳ + "Verifying SHA256..." 文字
  - **下載失敗**（`downloadStatus='failed'`）：❌ + 錯誤訊息 + Retry 按鈕
  - **已取消**（`downloadStatus='cancelled'`）：❌ + "Cancelled" + Download 按鈕（可重新下載）
- 進度條樣式：
  - 使用 PrimeVue `<ProgressBar>` 元件（ComfyUI 的 Model Library 下載也是用此元件）
  - 自動適應 ComfyUI 深色/淺色主題（PrimeVue 已配置 `darkModeSelector`）
  - 搭配 `:show-value="progress > 10"` 在進度條內顯示百分比
  - 進度條下方顯示 `已下載 / 總量` 的 MB 文字（例如 `96.5 / 144.0 MB`）
- 新增 emits：`download`、`cancel`、`retry`（由 ModelCard 向上傳遞事件給 ModelList → App）
- Download / Cancel / Retry 按鈕樣式：使用 ComfyUI CSS 變數，與現有 Go 按鈕風格一致

**相關檔案**
- `ui/src/types/index.ts` — 擴展 Resource 型別
- `ui/src/components/ModelCard.vue` — 主要修改：7 種狀態 UI
- `ui/src/components/ModelList.vue` — 傳遞事件、可能需要調整 missing count 計算

**完成檢查**
- `cd ui && npm run build` 建置成功無 TypeScript 錯誤
- 在 ComfyUI 中查詢 image ID 後：
  - 缺少的 model 卡片顯示 Download 按鈕
  - 已存在的 model 卡片不顯示 Download 按鈕
  - 未解析的 model 卡片顯示 "Cannot resolve"

**實作備註**
[方向調整] DownloadStatus 型別新增了 `'waiting'` 狀態（原計畫沒有），用於批次下載時等待中的 model 卡片顯示「Waiting...」文字。另外新增了 `hashes` 欄位到 Resource 型別，對應後端 resolve API 回傳的 SHA256 hash（來自任務一的後續依賴）。

---

### 實作前端下載流程整合（單一下載、批次下載、取消）

**實作要點**
- 擴展 `ui/src/composables/useCivitaiApi.ts`，新增下載相關函式：
  - `downloadModel(resource: Resource): Promise<{ task_id: string }>`
    - `POST /civitai/download` with `{ resource, api_key }`
  - `downloadAllMissing(resources: Resource[]): Promise<{ task_id: string }>`
    - `POST /civitai/download-all` with `{ resources, api_key }`
    - 只傳送 `resolved=true && !already_downloaded` 的 resources
  - `cancelDownload(taskId: string): Promise<void>`
    - `POST /civitai/download-cancel` with `{ task_id }`
  - `cancelAllDownloads(): Promise<void>`
    - `POST /civitai/download-cancel` with `{ cancel_all: true }`
- 在 `ui/src/App.vue` 中新增 WebSocket 事件監聽：
  - 使用 `window.app.api.addEventListener('civitai.download.progress', handler)` 監聽後端推送的進度事件
  - 根據 `task_id` 更新對應 resource 的 `downloadStatus`、`downloadProgress`、`downloadedBytes`、`totalBytes`
  - 當 status 為 `completed` 時，更新 `already_downloaded = true` 並移除下載狀態
  - 當 status 為 `failed` 時，設定 `downloadError`
  - 注意在元件 unmount 時移除事件監聽（`removeEventListener`）
- 修改 `ui/src/components/ModelList.vue`：
  - 新增「Download All Missing」按鈕（條件：有缺少且已解析的 model）
  - 下載進行中時，按鈕變為「Downloading... (X/Y)」+ disabled
  - 新增「Cancel All」按鈕（條件：有下載進行中）
  - 下載全部完成後，按鈕消失
  - 更新 missing count 計算：下載完成的不再計入 missing
- 整合事件流：
  - ModelCard emits `download` → ModelList → App.vue 呼叫 `downloadModel()`
  - ModelCard emits `cancel` → ModelList → App.vue 呼叫 `cancelDownload()`
  - ModelCard emits `retry` → ModelList → App.vue 呼叫 `downloadModel()`（同 download）
  - ModelList emits `download-all` → App.vue 呼叫 `downloadAllMissing()`
  - ModelList emits `cancel-all` → App.vue 呼叫 `cancelAllDownloads()`

**相關檔案**
- `ui/src/composables/useCivitaiApi.ts` — 新增 download/cancel API 函式
- `ui/src/App.vue` — WebSocket 監聽、下載狀態管理、事件處理
- `ui/src/components/ModelList.vue` — Download All / Cancel All 按鈕
- `ui/src/components/ModelCard.vue` — 確認事件正確 emit

**完成檢查**
- `cd ui && npm run build` 建置成功
- 在 ComfyUI 中完整測試下載流程：
  - 點擊單一 Download 按鈕 → 進度條出現 → 完成後切換為 ✅
  - 點擊 Download All Missing → 依序下載 → 全部完成後按鈕消失
  - 點擊 Cancel → 下載停止 → .part 檔案已清除 → 顯示 Download 按鈕可重試
  - 下載失敗 → 顯示錯誤訊息 + Retry 按鈕

**實作備註**
- [方向調整] `civitai_routes.py` 的 `_download_single()` 中，取消時的 `.part` 檔案清理原本在 `with open()` 區塊內呼叫 `_cleanup_part()`，但 Windows 上檔案鎖定導致刪除失敗。改為使用 `cancelled` flag + `break` 跳出迴圈，讓 `with` 區塊關閉檔案後再清理。

---

### 實作後端 Workflow 生成 API

**實作要點**
- 在 `civitai_routes.py` 中新增 API endpoint：
  - `POST /civitai/generate`：接受 `{ metadata, resources }`，回傳 workflow JSON
  - 直接呼叫 `pipeline/generate_workflow.py` 的 `build_workflow(metadata, resources)` 函式
  - `build_workflow()` 回傳的是 API format（flat dict with node IDs as string keys）
  - 需要研究 `app.loadGraphData()` 接受的格式：
    - 如果接受 API format → 直接回傳
    - 如果需要 graph format（含 node 座標、link 資訊）→ 需要轉換
    - 另一個方案：使用 `/prompt` endpoint 直接提交執行（不載入 canvas）
    - 最可能的方案：ComfyUI 前端有 `app.loadApiJson(apiData)` 或類似方法可以從 API format 載入
- 處理 `build_workflow()` 可能拋出的例外：
  - 缺少必要的 metadata 欄位（如 prompt、sampler）
  - 不支援的 workflow 類型
  - resources 中沒有 checkpoint 模型
- 回傳結構：`{ workflow, workflow_type, node_count }`

**相關檔案**
- `civitai_routes.py` — 新增 `/civitai/generate` route
- `pipeline/generate_workflow.py` — 重用 `build_workflow()` 函式（不修改）
- `pipeline/sampler_map.py` — `build_workflow()` 內部使用（不修改）

**完成檢查**
- 使用 curl 測試 `POST /civitai/generate`：
  - 傳入有效的 metadata 和 resources → 回傳 workflow JSON
  - 回傳的 JSON 包含預期的 node（CheckpointLoaderSimple、KSampler 等）
  - 傳入無效資料 → 回傳適當的錯誤訊息和 HTTP status code

**實作備註**
- [方向調整] 原計畫說「不修改 generate_workflow.py」，但 `_extract_common_params()` 在找不到 checkpoint 時呼叫 `sys.exit(1)`，在 web server 環境中會直接關閉 ComfyUI 進程。改為拋出 `ValueError`，CLI 的 `main()` 不受影響（因為 `main()` 是唯一的入口，會在其之前就處理好）。
- [技術決策] 研究確認 ComfyUI 前端有 `app.loadApiJson(apiData, fileName)` 方法可直接載入 API format workflow（使用者也驗證過），不需要做 API format → graph format 轉換。後端直接回傳 `build_workflow()` 的結果即可。
- [後續依賴] 前端任務使用 `window.app.loadApiJson(workflow, filename)` 載入 workflow，而非 `loadGraphData()`。`loadApiJson` 會自動建立 nodes、連接 links 並排列。

---

### 實作前端 Workflow 生成與 Canvas 載入

**實作要點**
- 擴展 `ui/src/composables/useCivitaiApi.ts`：
  - `generateWorkflow(metadata: Metadata, resources: Resource[]): Promise<GenerateResponse>`
    - `POST /civitai/generate` with `{ metadata, resources }`
    - 回傳 `{ workflow, workflow_type, node_count }`
- 在 `ui/src/App.vue` 中新增 workflow 生成流程：
  - 新增 reactive state：`generatingWorkflow: boolean`、`workflowResult: { type, nodeCount } | null`
  - 點擊 Generate Workflow → 檢查是否有缺少的 model
    - 有缺少：顯示警告對話框（列出缺少的 model），使用者確認後繼續
    - 無缺少：直接生成
  - 呼叫 `generateWorkflow()` → 取得 workflow JSON
  - 使用 `window.app.loadApiJson(workflow, filename)` 載入到 canvas
    - ComfyUI 前端的 `loadApiJson()` 原生支援 API format，會自動建立 nodes 並排列
    - `build_workflow()` 回傳的就是 API format，不需要任何格式轉換
  - 載入成功後在 sidebar 顯示確認訊息（workflow type + node count）
- 新增 UI 元件或在 ModelList 下方新增區域：
  - 「Generate Workflow」按鈕（條件：metadata 已載入）
  - 生成中：按鈕 disabled + spinner
  - 缺少模型警告對話框：列出缺少的 model name + type，Cancel / Continue 按鈕
  - 成功確認訊息：✅ Workflow loaded · {nodeCount} nodes · {workflowType}
- 擴展 `ui/src/types/index.ts`：
  - 新增 `GenerateResponse` 型別

**相關檔案**
- `ui/src/composables/useCivitaiApi.ts` — 新增 generateWorkflow 函式
- `ui/src/App.vue` — workflow 生成流程、狀態管理、警告對話框
- `ui/src/components/ModelList.vue` — Generate Workflow 按鈕位置、確認訊息
- `ui/src/types/index.ts` — 新增 GenerateResponse 型別
- `ui/src/types/comfyui.d.ts` — 新增 `loadApiJson` 型別宣告

**完成檢查**
- `cd ui && npm run build` 建置成功
- 在 ComfyUI 中測試：
  - 所有模型已存在時：點擊 Generate Workflow → canvas 載入 workflow → 顯示確認訊息
  - 有缺少模型時：點擊 Generate Workflow → 顯示警告 → 點 Continue → canvas 載入 workflow
  - 警告對話框點 Cancel → 不生成 workflow
  - 使用三個測試 image ID（116872916、118577644、119258762）驗證不同 workflow type

**實作備註**
照預期開發

---

### 研究 Workflow 節點自動排版方案

**背景**
ComfyUI 的 `loadApiJson()` 內建的 `arrange()` 無法正確排列節點（所有節點堆疊在 (10,10)）。這是 ComfyUI 前端本身的問題：`loadApiJson` 在呼叫 `arrange()` 前沒有先對節點執行 `computeSize()`/`setSize()`，導致排列演算法使用預設尺寸而失效。即使手動拖放 API format JSON 檔案到 ComfyUI 也會有同樣問題。

**研究目標**
找出一個方案，讓生成的 workflow 載入 ComfyUI canvas 時節點能正確排列，不互相重疊。

**研究方向**
1. **後端計算節點座標（Graph format 輸出）**：
   - `build_workflow()` 目前輸出 API format（flat dict, string keys as node IDs）
   - ComfyUI 的 graph format 包含每個節點的 `pos`（座標）、`size`（尺寸）、`links`（連接資訊）
   - 是否可以在後端將 API format 轉換為 graph format，自行計算每個節點的座標？
   - 需要研究 graph format 的完整結構（參考 ComfyUI 預設 workflow 或匯出的 workflow）
   - 排版演算法：按 DAG 依賴層級從左到右排列（類似 LiteGraph 的 `arrange()`）
   - 需要估算每個節點的寬度和高度（根據 class_type 和 widget 數量）
2. **前端載入後觸發排版**：
   - 改用 `loadGraphData()` 而非 `loadApiJson()`，傳入帶座標的 graph format
   - 或在 `loadApiJson()` 後用其他方式觸發正確的排版
   - 研究是否有第三方 ComfyUI extension 的排版方案可參考（如 comfyui-auto-nodes-layout 使用 ELK.js）
3. **混合方案**：
   - 後端生成帶有基本座標的 graph format
   - 前端載入後可選擇性地微調

**研究產出**
- 確定最佳方案（後端 vs 前端 vs 混合）
- 如果是後端方案：定義 graph format 結構、節點尺寸估算規則、排版演算法
- 如果是前端方案：確認可行的 API 呼叫方式

**相關檔案**
- `pipeline/generate_workflow.py` — 目前的 workflow 生成邏輯
- ComfyUI frontend `src/scripts/app.ts` — `loadApiJson()` 和 `loadGraphData()` 實作
- ComfyUI frontend `src/lib/litegraph/src/LGraph.ts` — `arrange()` 實作

**實作備註**
[技術決策] 比較三個方案：(A) 前端修復 — loadApiJson 後手動呼叫 computeSize+arrange、(B) 後端生成 Graph Format — 在 Python 中計算座標、(C) Monkey-patch loadApiJson。選擇方案 A，原因：
1. computeSize() 需要瀏覽器 canvas context 測量文字寬度（LGraphCanvas._measureText 使用 ctx.measureText），後端無法精確計算
2. 方案 A 只需在 App.vue 中 loadApiJson 後加 3 行程式碼（遍歷 nodes → computeSize → setSize → arrange）
3. 不修改 ComfyUI 核心、不影響其他 extension
4. window.app.graph._nodes 和 window.app.graph.arrange() 在 extension 中可直接存取（已確認 app.graph === app.rootGraph）

---

### 實作 Workflow 節點自動排版

**實作要點**
- 修改 `ui/src/App.vue` 中呼叫 `loadApiJson` 的程式碼，在載入後加入排版修復：
  ```typescript
  // 載入 API format workflow
  window.app.loadApiJson(workflow, filename)

  // Fix: loadApiJson's arrange() fails because it doesn't call computeSize() first.
  // Manually compute sizes and re-arrange after loading.
  for (const node of window.app.graph._nodes) {
    const size = node.computeSize()
    node.setSize(size)
  }
  window.app.graph.arrange()
  ```
- 更新 `ui/src/types/comfyui.d.ts` 型別宣告，新增 `graph` 屬性的型別（包含 `_nodes` 和 `arrange()`）
- 不需要修改後端 `generate_workflow.py`，繼續輸出 API format

**相關檔案**
- `ui/src/App.vue` — 在 loadApiJson 呼叫後加入排版修復邏輯
- `ui/src/types/comfyui.d.ts` — 新增 graph 相關型別宣告

**完成檢查**
- 使用三個測試 image ID（116872916、118577644、119258762）生成 workflow 後，節點在 canvas 上正確排列、不互相重疊
- 連接線清晰可見，從左到右依照依賴順序排列
- `cd ui && npm run build` 建置成功（如有前端修改）

**實作備註**
在 `App.vue` 的 `doGenerateWorkflow()` 中，`loadApiJson()` 呼叫後加入 3 行修復：遍歷所有節點 → `computeSize()` → `setSize()` → 最後 `graph.arrange()`。問題根因是 `loadApiJson` 內部的 `arrange()` 使用預設 node size（尚未經過 `computeSize`），導致排版間距不正確。修復後節點正確依 DAG 層級從左到右排列。

注意：初始研究認為 `arrange()` 在 LiteGraph 資料層失敗，但 debug 後發現 `arrange()` 確實正常運作（`pos` 值正確分布）。實際問題是 Vue renderer 需要透過 `setSize()` 觸發響應式更新才能正確反映位置。用戶手動切換 renderer 設定後確認修復有效。

---

### 發佈準備（版本號、README）

**實作要點**
- 確認 `pyproject.toml` 的 `[tool.comfy]` 區段完整且正確：
  - 已有 `PublisherId`、`DisplayName`、`Icon`、`includes` — 確認值是否需要更新
- 確認版本號：`version = "0.1.0"`（首次發佈）
- 確認 `js/main.js` 已納入 git 追蹤（Phase 2 末期已完成，commit `14cd8f1`）
- 更新 `README.md`：
  - 新增 ComfyUI Manager 安裝方式說明
  - 新增手動安裝方式說明（git clone → 無需建置前端）
  - 新增 sidebar extension 使用教學
  - 新增支援的 workflow 類型說明（txt2img、txt2img-hires）
  - 更新 troubleshooting 區段

**備註**
- GitHub Actions（`.github/workflows/publish.yml`、`.github/workflows/ci.yml`）暫不建立，待後續需要時再處理

**相關檔案**
- `pyproject.toml` — 確認 `[tool.comfy]` 設定
- `README.md` — 更新安裝和使用說明

**完成檢查**
- `pyproject.toml` 包含完整的 `[tool.comfy]` 區段
- `README.md` 包含 ComfyUI Manager 安裝說明和 sidebar 使用教學

**實作備註**
照預期開發

---

### 執行驗收測試

**實作要點**
- 讀取 `acceptance.feature` 檔案
- 在 ComfyUI 環境中逐一執行每個場景（使用 Playwright MCP 連線至 ComfyUI 頁面自動化執行驗收場景）
- 驗證所有場景通過並記錄結果
- 如發現問題，記錄詳細的錯誤資訊和重現步驟

**相關檔案**
- `docs/specs/2026-01-31-sidebar-extension-phase3-5/acceptance.feature` — Gherkin 格式的驗收測試場景
- `docs/specs/2026-01-31-sidebar-extension-phase3-5/acceptance-report.md` — 詳細的驗收測試執行報告（執行時生成）

**實作備註**
<!-- 執行過程中填寫 -->

---

### 更新專案文件

**實作要點**
- 審查 `README.md`，根據新功能更新：
  - 新增模型下載功能描述
  - 新增 workflow 生成功能描述
  - 更新功能清單
  - 更新專案結構圖（如有新增檔案）
- 審查 `CLAUDE.md`，更新：
  - 新增下載 API endpoints 說明（`/civitai/download`、`/civitai/download-all`、`/civitai/download-cancel`、`/civitai/generate`）
  - 更新 Supported Scope 章節，將 Phase 3-5 功能從 "Not Yet Supported" 移至已支援
  - 更新前端架構說明（新增元件、WebSocket 監聽）
  - 更新 UI 狀態機說明（7 個狀態）
- 確保所有程式碼範例和指令都是最新且可執行的
- **注意**：不需要更新 `docs/research/` 和 `docs/specs/` 目錄中的歷史文件

**相關檔案**
- `README.md` — 專案主要說明文件
- `CLAUDE.md` — AI 助手的專案指引文件

**實作備註**
<!-- 執行過程中填寫 -->

---

## 實作參考資訊

### 來自研究文件的技術洞察
> **文件路徑：** `docs/research/2026-01-31-comfyui-sidebar-extension.md`

**WebSocket 進度推送機制：**

ComfyUI 的 `PromptServer` 提供 `send_sync()` 方法，可以向所有連線的 WebSocket 客戶端推送事件：

```python
# 後端推送進度
PromptServer.instance.send_sync("civitai.download.progress", {
    "task_id": "uuid-here",
    "filename": "model.safetensors",
    "status": "downloading",
    "progress": 67,
    "downloaded_bytes": 96_000_000,
    "total_bytes": 144_000_000
})
```

```typescript
// 前端監聽進度
window.app.api.addEventListener("civitai.download.progress", (event) => {
    const { task_id, filename, status, progress } = event.detail
    // 更新對應 resource 的下載狀態
})
```

**非同步下載不阻塞 event loop：**

ComfyUI 的後端是 aiohttp，所有 route handler 都在同一個 asyncio event loop 上執行。下載大型模型檔案（2-7 GB）時，必須確保不阻塞 event loop：

- 方案 A：使用 `aiohttp.ClientSession` 進行非同步 HTTP 下載（推薦）
- 方案 B：使用 `asyncio.to_thread()` 將同步的 `requests` 下載放到線程池
- 方案 A 更好，因為可以精確控制 chunk 大小和進度回報

**Civitai 下載認證：**

Civitai 的模型下載 URL 需要 API key 認證，方式為在 URL 查詢參數中加入 `token`：
```
https://civitai.com/api/download/models/12345?token=sk_xxxxx
```

### 來自 PRD 的實作細節

**UI 狀態機（7 個狀態）：**
- 階段 0：API Key 未設定（已完成）
- 階段 1：正常輸入狀態（已完成）
- 階段 2：載入中（已完成）
- 階段 3：結果展示 + Download 按鈕 + Generate Workflow 按鈕（Phase 3-4 新增）
- 階段 4：下載中 — Model 卡片內進度條（Phase 3 新增）
- 階段 5：Workflow 生成中（Phase 4 新增）
- 階段 6：完成 — Workflow 已載入到 canvas（Phase 4 新增）

**Model 卡片 7 種視覺狀態：**
1. 已存在：✅ + 路徑
2. 缺少（已解析）：❌ + Download 按鈕
3. 缺少（未解析）：❌ + "Cannot resolve"
4. 下載中：⏳ + 進度條 + Cancel 按鈕
5. 校驗中：⏳ + "Verifying SHA256..."
6. 下載失敗：❌ + 錯誤訊息 + Retry 按鈕
7. 已取消：❌ + "Cancelled" + Download 按鈕

**下載流程（`.part` + SHA256）：**
1. 開始下載 → 寫入 `model.safetensors.part`
2. 下載完成 → 計算 SHA256（`hashlib.sha256`）
3. 比對 Civitai API 提供的 `hashes.SHA256`
4. 校驗成功 → rename `.part` 為正式檔名
5. 校驗失敗 / 取消 → 刪除 `.part` 檔案

**CSS 風格延續：**
- 使用 ComfyUI 原生 CSS 變數（`--fg-color`、`--descrip-text`、`--border-color`、`--comfy-input-bg`）
- 不使用 PrimeVue tokens（`--p-text-color` 等），因為不隨 ComfyUI 深色主題切換
- 進度條使用 PrimeVue `<ProgressBar>` 元件（ComfyUI Model Library 也使用此元件，自動適應主題）

**Workflow 格式問題（開放問題）：**
- `build_workflow()` 回傳 API format（flat dict, string keys as node IDs）
- `app.loadGraphData()` 可能需要 graph format（含 node 座標、link 資訊）
- 需要在實作時確認：
  - 嘗試直接傳入 API format
  - 如果不行，嘗試 `app.loadApiJson()` 或其他方法
  - 最後方案：包裝成 `{ workflow: apiData }` 格式
  - 備選方案：使用 `/prompt` endpoint 直接提交執行（但不載入 canvas）

### 關鍵技術決策

1. **非同步下載方式**：使用 `aiohttp.ClientSession`（非同步 HTTP 客戶端）而非 `requests`（同步），避免阻塞 ComfyUI 的 aiohttp event loop。進度透過 WebSocket 推送。

2. **下載檔案安全機制**：`.part` 暫存檔 + SHA256 校驗 + rename。確保取消或失敗不會留下不完整的模型檔案，避免 ComfyUI 載入損壞的模型。

3. **前端狀態管理**：所有下載狀態（progress、error、cancel）都掛在 `Resource` 物件上，透過 App.vue 的 reactive state 統一管理。WebSocket 事件透過 `window.app.api.addEventListener()` 監聽。

4. **Workflow 生成重用**：直接呼叫 `build_workflow()` 函式，不重新實作。這個函式已經過三個測試 image 的驗證，支援 txt2img 和 txt2img-hires 工作流。

5. **發佈策略**：`js/main.js` 已納入 git 追蹤，確保 git clone 安裝不需要建置前端。GitHub Actions 在 tag push 時自動發佈到 ComfyUI Registry。

6. **Phase 1-2 技術教訓延續**：
   - 模組命名不與 ComfyUI 內建模組衝突（`civitai_utils/` 而非 `utils/`）
   - 路由使用裝飾器模式（`@routes.post()`）
   - CSS 使用 ComfyUI 原生變數而非 PrimeVue tokens
   - Vite library mode 需要 `vite-plugin-css-injected-by-js`
   - 前端透過 `window.app` 全域物件存取 ComfyUI API
