# PRD: Civitai Alchemist ComfyUI Sidebar Extension（第一、二階段）

## 簡介/概述

Civitai Alchemist 目前是一個純 Python CLI 工具，使用者需要在終端機操作 4 個步驟才能從 Civitai 圖片重建生成環境。本 PRD 定義將此工具整合為 ComfyUI 原生 sidebar extension 的第一、二階段功能：建立基礎框架並串接核心的 metadata 查詢與 model 解析功能。

完成後，使用者可以直接在 ComfyUI 左側面板輸入 Civitai image ID，即時查看該圖片的生成參數（prompt、sampler、steps 等）以及所需 model 的存在狀態，無需離開 ComfyUI 介面。

本 PRD 基於 `docs/research/2026-01-31-comfyui-sidebar-extension.md` 中的技術研究發現。

## 目標

1. **在 ComfyUI 左側 sidebar 新增 Civitai Alchemist tab**，讓使用者可以直接在 ComfyUI UI 中操作
2. **實作 Civitai API Key 設定機制**，透過 ComfyUI 內建 Settings 系統管理，符合社群慣例
3. **實作 image metadata 查詢功能**，使用者輸入 image ID 或 URL 後可查看生成參數
4. **實作 model 解析與狀態檢查**，顯示所需 model 列表及哪些已存在、哪些缺少
5. **重構 pyproject.toml**，為 ComfyUI Registry 發佈做準備，清理不合理的相依性

## 使用者故事

### US-1：首次使用 — API Key 設定

作為 ComfyUI 使用者，我安裝了 Civitai Alchemist extension 後，第一次點開左側 sidebar 的 Civitai Alchemist tab。面板告訴我需要先設定 Civitai API Key，並提供一個按鈕可以直接開啟 ComfyUI Settings 面板到對應位置。我在 Settings 中輸入 API key 後，回到 sidebar，輸入功能已經可以使用。

### US-2：查詢圖片生成資訊

作為 ComfyUI 使用者，我在 Civitai 上看到一張喜歡的圖片。我在 sidebar 輸入該圖片的 ID（或貼上完整 URL），點擊 Go 按鈕。系統顯示載入中狀態，然後展示這張圖片的完整生成參數：prompt、negative prompt、sampler、steps、CFG、seed、圖片尺寸、clip skip 等。

### US-3：檢查 model 狀態

在查詢到生成資訊後，系統自動顯示該圖片使用的所有 model（checkpoint、LoRA、VAE、embedding 等）。每個 model 清楚標示是已存在（顯示在本地的哪個目錄）還是缺少。我可以快速了解要重現這張圖片還缺少哪些 model。

### US-4：更換查詢目標

我可以隨時在輸入欄位更換 image ID 或 URL，重新查詢另一張圖片的資訊。新的查詢結果會取代先前的顯示。

## 功能需求

### FR-1：Sidebar Tab 註冊

1. 在 ComfyUI 左側 sidebar 新增一個 Civitai Alchemist tab，帶有辨識度高的 icon
2. 點擊 icon 後展開 sidebar panel，顯示操作介面
3. Panel 寬度遵循 ComfyUI sidebar 慣例（約 300px），內容可捲動

### FR-2：API Key 管理

1. 透過 ComfyUI 內建的 Settings 系統（`Ctrl + ,`）提供 API key 輸入欄位
2. API key 欄位以密碼遮罩方式顯示（type: password）
3. API key 持久化儲存於 ComfyUI 的 settings 檔案中
4. Sidebar 開啟時自動檢查 API key 是否已設定
5. 若未設定，顯示提示訊息並提供「Open Settings」按鈕
6. 未設定 API key 時，Image ID 輸入欄位和 Go 按鈕設為 disabled

### FR-3：Image ID 輸入

1. 提供輸入欄位，接受以下兩種格式：
   - 純數字 ID（如 `116872916`）
   - 完整 Civitai image URL（如 `https://civitai.com/images/116872916`）
2. 提供 Go 按鈕觸發查詢
3. 輸入欄位支援按 Enter 觸發查詢（與點擊 Go 按鈕等效）
4. URL 格式自動解析出 image ID

### FR-4：載入狀態

1. 點擊 Go 後顯示載入中狀態（progress bar 或 spinner + 文字提示）
2. 載入中狀態文字依序顯示目前步驟：「Fetching metadata...」→「Resolving models...」
3. 載入期間，Go 按鈕設為 disabled 避免重複查詢

### FR-5：生成參數展示

查詢成功後顯示以下生成參數（有值才顯示）：

1. **Prompt** — 正向提示詞（可摺疊，避免太長佔據空間）
2. **Negative Prompt** — 反向提示詞（可摺疊）
3. **Sampler** — 取樣器名稱
4. **Steps** — 取樣步數
5. **CFG Scale** — CFG 引導比例
6. **Seed** — 隨機種子
7. **Size** — 圖片尺寸（寬 x 高）
8. **Clip Skip** — Clip Skip 值

### FR-6：Model 列表展示

1. 以卡片形式展示所有所需 model
2. 每張卡片包含：
   - Model 名稱
   - Model 類型（Checkpoint、LoRA、VAE、Embedding 等）
   - 檔案大小
   - 狀態標示：已存在（✅ + 本地路徑）或 缺少（❌）
3. 列表上方或下方顯示摘要：「Missing: X of Y」
4. Model 存在狀態的檢查使用 ComfyUI 內建的 `folder_paths` API，確保搜尋路徑與使用者在 ComfyUI 中設定的 models 目錄一致（包含透過 `extra_model_paths.yaml` 或 CLI 參數自訂的路徑）
5. 本階段不顯示任何下載按鈕

### FR-7：錯誤處理

1. **API key 無效**：顯示清楚的錯誤訊息（如 Civitai API 回傳 401）
2. **Image ID 不存在**：顯示「Image not found」錯誤訊息
3. **網路錯誤**：顯示連線失敗訊息，提供重試機制
4. **無效輸入格式**：輸入既不是純數字也不是合法 Civitai URL 時，提示格式錯誤

### FR-8：後端 API Endpoints

1. `POST /civitai/fetch`：接受 image ID 和 api_key，呼叫 Civitai API 取得 metadata，回傳生成參數
2. `POST /civitai/resolve`：接受 metadata 和 api_key，解析所需 model 資訊，檢查本地是否已存在，回傳 model 列表（含名稱、類型、大小、存在狀態、本地路徑）

### FR-9：pyproject.toml 重構

1. `[project.dependencies]` 只保留 ComfyUI runtime 未提供的套件（`requests`）
2. `tqdm` 和 `python-dotenv` 移至 `[project.optional-dependencies].cli`，供 CLI 模式使用者安裝
3. 移除 `[project.optional-dependencies].dev`（ComfyUI runtime 套件）
4. 移除 `[[tool.uv.index]]` 和 `[tool.uv.sources]`（本地開發用 PyTorch CUDA 設定）
5. 新增 `[tool.comfy]` 區段，設定 `PublisherId`、`DisplayName`、`includes = ["js/"]`
6. 新增 `[project.urls]` 和 `license`
7. Pipeline 程式碼中 `import tqdm` 和 `from dotenv import load_dotenv` 加上 try/except，確保 custom node 模式下不因缺少這些套件而崩潰

### FR-10：前端建置環境

1. 建立 Vue 3 + TypeScript + PrimeVue 前端專案（位於 `ui/` 目錄）
2. 使用 Vite library mode 建置，輸出至 `js/` 目錄
3. ComfyUI 透過 `WEB_DIRECTORY = "./js"` 自動載入建置後的 JS 檔案

### FR-11：`__init__.py` 入口改動

1. 設定 `WEB_DIRECTORY = "./js"` 讓 ComfyUI 載入前端 JS
2. 在模組載入時註冊自定義 API routes

## 非目標（超出範圍）

1. **Model 下載功能**：不包含任何下載按鈕或下載進度功能（第三階段處理）
2. **Workflow 產生功能**：不包含 Generate Workflow 按鈕或 workflow 載入到 canvas（第四階段處理）
3. **ComfyUI Registry 實際發佈**：本階段只準備好 pyproject.toml，不包含實際發佈流程和 GitHub Actions
4. **ComfyUI custom nodes**：不新增任何 ComfyUI custom node（如自定義取樣器等）
5. **img2img / inpainting / ControlNet**：不在支援範圍
6. **CLI 工具的行為變更**：現有 CLI pipeline 功能維持不變，重構只是讓 import 更靈活

## 設計考量

### UI 設計

遵循研究文件中的 ASCII UI mockup。本階段涉及的畫面狀態：

- **階段 0**：API Key 未設定 — 提示訊息 + Open Settings 按鈕 + disabled 輸入欄位
- **階段 1**：正常輸入狀態 — Image ID/URL 輸入欄位 + Go 按鈕
- **階段 2**：載入中 — Progress bar/spinner + 步驟文字
- **階段 3**（部分）：資訊展示 — Generation Info + Model 列表（不含 Download 和 Generate Workflow 區塊）

### 視覺風格

- 使用 PrimeVue 元件（Button、InputText、ProgressBar、Card、Tag 等），確保與 ComfyUI 原生 UI 視覺風格一致
- Model 狀態使用明確的視覺標示（✅ 已存在 / ❌ 缺少）
- Prompt 文字區域可摺疊，避免佔據過多空間

## 技術考量

- 前端使用 Vue 3 + TypeScript + PrimeVue，與 ComfyUI 原生前端技術棧一致（基於研究文件的技術選型）
- 後端使用 aiohttp routes 註冊自定義 API endpoint，透過 `PromptServer.instance.routes` 整合
- 前端使用 `api.fetchApi()` 呼叫後端 API，API key 由前端從 ComfyUI Settings 讀取後帶入每個 request
- 現有 pipeline 模組需重構，將核心邏輯從 `main()` 函式中抽出為可獨立呼叫的函式
- 資料在 API 模式下透過參數傳遞，不再經由檔案系統中間產物（`output/*.json`）
- Model 存在狀態檢查改用 ComfyUI 內建的 `folder_paths` 模組（而非現有 CLI 模式的 `ModelManager` 自訂路徑），以正確對應使用者在 ComfyUI 中設定的 models 目錄（跨平台，支援 `extra_model_paths.yaml` 等自訂路徑設定）
- `pyproject.toml` 重構需確保 CLI 模式（`pip install -e ".[cli]"`）和 custom node 模式都能正常運作

## 開放問題

1. **PrimeVue 版本管理**：sidebar extension 內嵌的 PrimeVue 版本是否可能與 ComfyUI 前端的版本衝突？需要在實作時確認是否需要 scoped styles 或其他隔離措施。
2. **Hatch build 配置**：現有的 `[tool.hatch.build.targets.wheel] packages = ["."]` 在加入 `ui/` 目錄後，是否需要調整以排除前端原始碼（只保留建置後的 `js/`）。

## 參考資料

- [ComfyUI Sidebar Extension 研究文件](../../research/2026-01-31-comfyui-sidebar-extension.md) — 本 PRD 的技術基礎
- [Sidebar Tabs API](https://docs.comfy.org/custom-nodes/js/javascript_sidebar_tabs) — ComfyUI sidebar tab 註冊文件
- [Extension Settings API](https://docs.comfy.org/custom-nodes/js/javascript_settings) — ComfyUI Settings 欄位註冊文件
- [ComfyUI Dependencies](https://docs.comfy.org/development/core-concepts/dependencies) — ComfyUI runtime 提供的套件列表
- [pyproject.toml Specification](https://docs.comfy.org/registry/specifications) — ComfyUI Registry 規格
