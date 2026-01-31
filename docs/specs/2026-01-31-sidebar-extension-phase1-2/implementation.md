# 實作計畫

## 參考文件

**PRD 文件路徑：** `docs/specs/2026-01-31-sidebar-extension-phase1-2/prd.md`
**研究文件路徑：** `docs/research/2026-01-31-comfyui-sidebar-extension.md`

## 任務概要

- [ ] 重構 pyproject.toml 與 Pipeline 相容性調整
- [ ] 建立前端 Vue 3 專案與 Sidebar 框架
- [ ] 實作後端 API Routes 與 Pipeline 重構
- [ ] 實作前端 API Key 管理與 Image Input 元件
- [ ] 實作前端 Generation Info 與 Model List 元件
- [ ] 端對端整合測試與修正
- [ ] 執行驗收測試
- [ ] 更新專案文件

## 任務細節

### 重構 pyproject.toml 與 Pipeline 相容性調整

**實作要點**
- 修改 `pyproject.toml`：
  - `[project.dependencies]` 只保留 `requests>=2.31.0`
  - 新增 `[project.optional-dependencies].cli`，包含 `tqdm` 和 `python-dotenv`
  - 移除整個 `[project.optional-dependencies].dev`
  - 移除 `[[tool.uv.index]]` 和 `[tool.uv.sources]`
  - 新增 `[tool.comfy]` 區段（`PublisherId = "ThePhilosopherStone"`、`DisplayName = "Civitai Alchemist"`、`includes = ["js/"]`）
  - 新增 `[project.urls]`（Repository URL）
  - 新增 `license = { file = "LICENSE" }`
  - 新增 `LICENSE` 檔案（MIT License）
- 在 `utils/model_manager.py` 中將 `from tqdm import tqdm` 改為 try/except，讓 tqdm 為 optional
- 在 `pipeline/reproduce.py` 和其他 CLI 入口中，將 `from dotenv import load_dotenv` 改為 try/except
- 新增 `js/` 到 `.gitignore`（建置產出，不需版控）
- 確認 CLI 模式（`pip install -e ".[cli]"`）仍可正常運作

**相關檔案**
- `pyproject.toml` — 主要修改目標
- `LICENSE` — 新建：MIT License
- `utils/model_manager.py` — tqdm import 改為 optional
- `pipeline/reproduce.py` — load_dotenv import 改為 optional
- `pipeline/fetch_metadata.py` — load_dotenv import 改為 optional
- `pipeline/resolve_models.py` — load_dotenv import 改為 optional
- `pipeline/download_models.py` — load_dotenv import 改為 optional
- `pipeline/generate_workflow.py` — load_dotenv import 改為 optional
- `.gitignore` — 新增 `js/` 和 `ui/node_modules/`

**完成檢查**
- `pyproject.toml` 包含 `[tool.comfy]` 區段且 `dependencies` 只有 `requests`
- Pipeline CLI 指令仍可正常執行（`python -m pipeline.fetch_metadata --help` 無 import error）
- 在沒有 tqdm/dotenv 的環境中 import `utils.model_manager` 和 `pipeline.fetch_metadata` 不會崩潰

**實作備註**
<!-- 執行過程中填寫重要的技術決策、障礙和需要傳遞的上下文 -->

---

### 建立前端 Vue 3 專案與 Sidebar 框架

**實作要點**
- 在專案根目錄建立 `ui/` 目錄
- 初始化 Vue 3 + TypeScript + Vite 專案：
  - `package.json`：包含 `vue`、`primevue`、`@primevue/themes` 等依賴
  - `vite.config.ts`：library mode 建置，輸出到 `../js/`，format 為 ES module
  - `tsconfig.json`：TypeScript 設定
- 建立 `ui/src/main.ts` 作為前端入口：
  - 等待 `window.app?.extensionManager` 可用
  - 透過 `app.registerExtension()` 註冊 Settings（API Key 欄位，type: password）
  - 透過 `app.extensionManager.registerSidebarTab()` 註冊 sidebar tab
  - 在 sidebar tab 的 `render` callback 中建立 Vue app 並 mount
- 建立 `ui/src/App.vue` 作為 root component（初始為空白面板，顯示標題）
- 建立 `ui/src/types/index.ts` 定義 TypeScript 型別（Metadata、Resource 等）
- 建立 `ui/src/types/comfyui.d.ts` 宣告 `window.app` 和 ComfyUI API 的全域型別
- 執行 `npm run build` 確認可以正常建置到 `js/` 目錄
- 修改 `__init__.py`：
  - 新增 `WEB_DIRECTORY = "./js"`
  - 更新 `__all__` 匯出

**相關檔案**
- `ui/package.json` — 新建
- `ui/vite.config.ts` — 新建
- `ui/tsconfig.json` — 新建
- `ui/src/main.ts` — 新建：sidebar 和 settings 註冊入口
- `ui/src/App.vue` — 新建：root component
- `ui/src/types/index.ts` — 新建：型別定義
- `ui/src/types/comfyui.d.ts` — 新建：ComfyUI 全域型別宣告
- `__init__.py` — 修改：加入 WEB_DIRECTORY
- `js/` — 建置產出（gitignored）

**完成檢查**
- `cd ui && npm run build` 成功建置，`js/main.js` 存在
- `__init__.py` 包含 `WEB_DIRECTORY = "./js"`
- 啟動 ComfyUI 後，左側 sidebar 可以看到 Civitai Alchemist 的 tab icon，點擊後展開空白面板

**實作備註**
<!-- 執行過程中填寫重要的技術決策、障礙和需要傳遞的上下文 -->

---

### 實作後端 API Routes 與 Pipeline 重構

**實作要點**
- 建立 `api/__init__.py`（空檔案）
- 建立 `api/routes.py`，實作 `register_routes(server_instance)` 函式：
  - `POST /civitai/fetch`：接受 `{ image_id, api_key }`，回傳 metadata
    - 呼叫 `parse_image_id()` 解析輸入
    - 建立 `CivitaiAPI(api_key=...)` 實例
    - 呼叫 `api.get_image_metadata(image_id)` 取得原始資料
    - 呼叫 `extract_metadata(image_data)` 轉換格式
    - 回傳 JSON response
  - `POST /civitai/resolve`：接受 `{ metadata, api_key }`，回傳 resources 列表
    - 建立 `CivitaiAPI` 和 `ModelManager` 實例
    - ModelManager 改用 ComfyUI 的 `folder_paths` 取得 models 目錄（見實作參考資訊）
    - 對 metadata 中每個 resource 呼叫 `resolve_resource()`
    - 檢查每個 model 是否已存在（使用 `folder_paths.get_full_path()`）
    - 回傳包含存在狀態的 resources 列表
- 錯誤處理：
  - API key 無效（Civitai 回傳 401）→ 回傳 HTTP 401 + 錯誤訊息
  - Image ID 不存在（API 回傳 empty）→ 回傳 HTTP 404 + 錯誤訊息
  - 網路錯誤 → 回傳 HTTP 502 + 錯誤訊息
- 修改 `__init__.py`：在 module load 時呼叫 `register_routes(server.PromptServer.instance)`
- 在 `api/routes.py` 中建立一個適配函式或類別，使用 `folder_paths` API 來檢查 model 存在狀態，取代 `ModelManager.find_model()` 在 custom node 模式下的行為

**相關檔案**
- `api/__init__.py` — 新建
- `api/routes.py` — 新建：route handlers
- `__init__.py` — 修改：import 並呼叫 register_routes
- `pipeline/fetch_metadata.py` — 確認 `parse_image_id()` 和 `extract_metadata()` 可獨立呼叫
- `pipeline/resolve_models.py` — 確認 `resolve_resource()` 可獨立呼叫
- `utils/civitai_api.py` — 確認 `CivitaiAPI` 可用 api_key 參數建構
- `utils/model_manager.py` — 可能需要調整以支援 folder_paths

**完成檢查**
- 啟動 ComfyUI 後，使用 curl 測試：
  - `curl -X POST http://localhost:8188/civitai/fetch -H 'Content-Type: application/json' -d '{"image_id":"116872916","api_key":"YOUR_KEY"}'` 回傳 metadata JSON
  - `curl -X POST http://localhost:8188/civitai/resolve -H 'Content-Type: application/json' -d '{"metadata":...,"api_key":"YOUR_KEY"}'` 回傳 resources 列表，每個 resource 包含 `exists` 欄位
- 無效 image ID 回傳 HTTP 404，缺少 api_key 回傳 HTTP 401

**實作備註**
<!-- 執行過程中填寫重要的技術決策、障礙和需要傳遞的上下文 -->

---

### 實作前端 API Key 管理與 Image Input 元件

**實作要點**
- 建立 `ui/src/composables/useCivitaiApi.ts`：
  - `getApiKey()` 函式：透過 `window.app.extensionManager.setting.get('civitai-alchemist.api_key')` 讀取 API key
  - `fetchMetadata(imageId: string)` 函式：呼叫 `api.fetchApi('/civitai/fetch', ...)` 帶上 api_key
  - `resolveModels(metadata: Metadata)` 函式：呼叫 `api.fetchApi('/civitai/resolve', ...)` 帶上 api_key
  - 錯誤處理：解析 HTTP status code 並回傳用戶友好的錯誤訊息
- 建立 `ui/src/components/ApiKeyWarning.vue`：
  - 當 API key 未設定時顯示提示訊息
  - 包含「Open Settings」按鈕（呼叫 ComfyUI 的 settings panel 開啟功能）
- 建立 `ui/src/components/ImageInput.vue`：
  - InputText + Go Button 組合
  - 支援 Enter 鍵觸發查詢
  - API key 未設定時 disabled
  - 載入中時 Go 按鈕 disabled + 顯示 loading 狀態
  - 接受純數字 ID 或完整 URL
- 修改 `ui/src/App.vue`：
  - 管理整體狀態（apiKeySet、loading、metadata、resources、error）
  - 根據狀態切換顯示 ApiKeyWarning 或正常介面
  - 處理查詢流程：fetchMetadata → resolveModels → 更新 state
  - 載入中顯示 spinner + 步驟文字（「Fetching metadata...」→「Resolving models...」）
  - 錯誤發生時顯示錯誤訊息

**相關檔案**
- `ui/src/composables/useCivitaiApi.ts` — 新建
- `ui/src/components/ApiKeyWarning.vue` — 新建
- `ui/src/components/ImageInput.vue` — 新建
- `ui/src/App.vue` — 修改：整合狀態管理和元件
- `ui/src/types/index.ts` — 可能需更新型別定義

**完成檢查**
- 建置成功（`cd ui && npm run build`）
- 在 ComfyUI 中：未設定 API key 時顯示警告訊息和 Open Settings 按鈕
- 設定 API key 後，輸入欄位和 Go 按鈕變為可用
- 輸入 image ID 後點擊 Go，可以看到載入中狀態

**實作備註**
<!-- 執行過程中填寫重要的技術決策、障礙和需要傳遞的上下文 -->

---

### 實作前端 Generation Info 與 Model List 元件

**實作要點**
- 建立 `ui/src/components/GenerationInfo.vue`：
  - 展示 prompt（可摺疊）、negative prompt（可摺疊）
  - 展示 sampler、steps、CFG、seed、size、clip skip
  - 只顯示有值的欄位
  - 使用 PrimeVue 元件：Accordion/Panel 用於摺疊、Tag 用於標籤式展示
- 建立 `ui/src/components/ModelList.vue`：
  - Model 列表容器
  - 頂部或底部顯示摘要文字：「Missing: X of Y」
- 建立 `ui/src/components/ModelCard.vue`：
  - 顯示 model 名稱、類型（Tag）、檔案大小
  - 已存在：綠色 ✅ 標示 + 「Found in: {path}」
  - 缺少：紅色 ❌ 標示（不顯示下載按鈕，本階段不包含）
  - 使用 PrimeVue Card 元件
- 修改 `ui/src/App.vue`：
  - 查詢成功後顯示 GenerationInfo + ModelList
  - 傳入 metadata 和 resources 資料

**相關檔案**
- `ui/src/components/GenerationInfo.vue` — 新建
- `ui/src/components/ModelList.vue` — 新建
- `ui/src/components/ModelCard.vue` — 新建
- `ui/src/App.vue` — 修改：整合新元件
- `ui/src/types/index.ts` — 可能需更新

**完成檢查**
- 建置成功（`cd ui && npm run build`）
- 在 ComfyUI 中輸入有效 image ID 後：
  - 生成參數區域正確顯示 prompt、sampler、steps 等資訊
  - Model 列表正確顯示每個 model 的名稱、類型、大小
  - 已存在的 model 顯示 ✅ + 路徑
  - 缺少的 model 顯示 ❌
  - 摘要文字「Missing: X of Y」正確

**實作備註**
<!-- 執行過程中填寫重要的技術決策、障礙和需要傳遞的上下文 -->

---

### 端對端整合測試與修正

**實作要點**
- 使用已知可運作的測試 image ID（116872916、118577644、119258762）進行端對端測試
- 驗證完整流程：輸入 ID → 載入中 → 顯示生成參數 → 顯示 model 列表
- 確認錯誤處理行為：
  - 無效 image ID → 顯示錯誤訊息
  - 無效 API key → 顯示錯誤訊息
  - 空白輸入 → 適當提示
- 確認 UI 在不同狀態之間的切換正常：
  - API key 未設定 → 設定後 → 輸入 → 載入中 → 結果 → 更換 ID → 重新載入
- 修正在整合過程中發現的問題
- 確認 URL 格式輸入（`https://civitai.com/images/116872916`）可以正確解析

**相關檔案**
- 所有前端和後端檔案（視發現的問題而定）

**完成檢查**
- 三個測試 image ID 都可以正確完成完整流程
- 錯誤情境都有適當的錯誤訊息
- UI 狀態切換流暢無異常

**實作備註**
<!-- 執行過程中填寫重要的技術決策、障礙和需要傳遞的上下文 -->

---

### 執行驗收測試

**實作要點**
- 讀取 `acceptance.feature` 檔案
- 在 ComfyUI 環境中逐一執行每個場景
- 驗證所有場景通過並記錄結果
- 如發現問題，記錄詳細的錯誤資訊和重現步驟

**相關檔案**
- `docs/specs/2026-01-31-sidebar-extension-phase1-2/acceptance.feature` — Gherkin 格式的驗收測試場景
- `docs/specs/2026-01-31-sidebar-extension-phase1-2/acceptance-report.md` — 詳細的驗收測試執行報告（執行時生成）

**實作備註**
<!-- 執行過程中填寫 -->

---

### 更新專案文件

**實作要點**
- 審查 `README.md`，更新：
  - 新增 ComfyUI Extension 安裝和使用說明
  - 新增 sidebar 功能描述
  - 更新專案結構圖
  - 新增前端開發說明（`cd ui && npm install && npm run build`）
- 審查 `CLAUDE.md`，更新：
  - 新增 `ui/` 和 `api/` 目錄到專案結構
  - 新增前端建置說明
  - 更新 pyproject.toml 相關說明
  - 新增 ComfyUI Extension 開發相關資訊
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

**Sidebar 和 Settings 註冊方式：**

```typescript
// main.ts — 等待 ComfyUI app 可用後註冊
async function init() {
  while (!window.app?.extensionManager) {
    await new Promise(r => setTimeout(r, 50))
  }

  // 註冊 Settings（API Key）
  window.app.registerExtension({
    name: 'civitai-alchemist',
    settings: [{
      id: 'civitai-alchemist.api_key',
      name: 'Civitai API Key',
      type: 'text',
      defaultValue: '',
      tooltip: 'Generate at https://civitai.com/user/account',
      attrs: { type: 'password', placeholder: 'sk_...' }
    }]
  })

  // 註冊 Sidebar Tab
  window.app.extensionManager.registerSidebarTab({
    id: 'civitai-alchemist',
    icon: 'pi pi-bolt',
    title: 'Civitai Alchemist',
    tooltip: 'Reproduce Civitai images',
    type: 'custom',
    render: (el) => {
      const container = document.createElement('div')
      el.appendChild(container)
      const vueApp = createApp(App)
      vueApp.use(PrimeVue)
      vueApp.mount(container)
    }
  })
}
```

**前端讀取 API Key：**

```typescript
function getApiKey(): string {
  return window.app.extensionManager.setting.get('civitai-alchemist.api_key') || ''
}
```

**前端呼叫後端 API：**

```typescript
async function fetchMetadata(imageId: string) {
  const response = await api.fetchApi('/civitai/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id: imageId, api_key: getApiKey() })
  })
  return response.json()
}
```

**Vite 建置設定（library mode）：**

```typescript
export default defineConfig({
  plugins: [vue()],
  build: {
    lib: {
      entry: resolve(__dirname, './src/main.ts'),
      formats: ['es'],
      fileName: 'main'
    },
    rollupOptions: {
      external: ['../../../scripts/app.js'],
      output: {
        dir: '../js',
        entryFileNames: 'main.js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    },
    sourcemap: true,
    minify: false
  }
})
```

**`__init__.py` 結構：**

```python
import os
import server

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

# Register custom API routes
from .api.routes import register_routes
register_routes(server.PromptServer.instance)
```

**`api/routes.py` 結構：**

```python
from aiohttp import web
from server import PromptServer

def register_routes(server_instance: PromptServer):
    @server_instance.routes.post("/civitai/fetch")
    async def fetch_metadata(request):
        data = await request.json()
        # ... call pipeline functions
        return web.json_response(metadata)

    @server_instance.routes.post("/civitai/resolve")
    async def resolve_models(request):
        data = await request.json()
        # ... call pipeline functions
        return web.json_response(resources)
```

**pyproject.toml 目標結構：**

```toml
[project]
name = "comfyui-civitai-alchemist"
description = "Reproduce Civitai images locally via ComfyUI"
version = "0.1.0"
license = { file = "LICENSE" }
requires-python = ">=3.10,<3.13"
dependencies = ["requests>=2.31.0"]

[project.optional-dependencies]
cli = ["tqdm", "python-dotenv"]

[project.urls]
Repository = "https://github.com/ThePhilosopherStone/comfyui-civitai-alchemist"

[tool.comfy]
PublisherId = "ThePhilosopherStone"
DisplayName = "Civitai Alchemist"
Icon = ""
includes = ["js/"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["."]
```

### 來自 PRD 的實作細節

**UI 狀態機（本階段涉及的 4 個狀態）：**
- 階段 0：API Key 未設定 → 提示訊息 + Open Settings 按鈕 + disabled 輸入欄位
- 階段 1：正常輸入狀態 → Image ID/URL 輸入欄位 + Go 按鈕
- 階段 2：載入中 → Progress/spinner + 步驟文字
- 階段 3（部分）：結果展示 → Generation Info + Model 列表（不含 Download 和 Generate）

**錯誤處理規格：**
- API key 無效（401）→ 顯示「Invalid API key」
- Image ID 不存在（404）→ 顯示「Image not found」
- 網路錯誤 → 顯示連線失敗訊息 + 重試機制
- 無效輸入格式 → 提示格式錯誤

**Model 存在狀態檢查 — 使用 `folder_paths` API：**

在 custom node 模式下，model 搜尋路徑必須使用 ComfyUI 的 `folder_paths` 模組，而非 `ModelManager` 的自訂路徑。這確保搜尋路徑與使用者在 ComfyUI 中設定的 models 目錄一致。

```python
import folder_paths

# 取得特定類型的搜尋路徑
paths = folder_paths.get_folder_paths("checkpoints")

# 列出所有已存在的 model 檔案
models = folder_paths.get_filename_list("loras")

# 查找特定 model
path = folder_paths.get_full_path("checkpoints", "model.safetensors")
```

`folder_paths` 的型別映射（Civitai type → ComfyUI folder_paths name）：
- `checkpoint` → `"checkpoints"`
- `lora` → `"loras"`
- `vae` → `"vae"`
- `embedding` → `"embeddings"`
- `upscaler` → `"upscale_models"`

### 關鍵技術決策

1. **前端技術棧**：Vue 3 + TypeScript + PrimeVue，透過 Vite library mode 建置。選擇 Vue 3 是因為與 ComfyUI 原生前端一致，可以直接使用 PrimeVue 元件。

2. **API Key 管理**：使用 ComfyUI 內建 Settings 系統而非自建設定頁。Settings 持久化到 `comfy.settings.json`，前端透過 `extensionManager.setting.get()` 讀取。

3. **Model 路徑解析**：custom node 模式使用 `folder_paths` API，CLI 模式保留 `ModelManager`。`api/routes.py` 中直接使用 `folder_paths`，不經過 `ModelManager`。

4. **Pipeline 重構策略**：不修改現有函式簽名，只讓 `main()` 中的 import 更 resilient（try/except）。API layer 直接呼叫已存在的核心函式（`extract_metadata()`、`resolve_resource()` 等），不需要大幅重構。

5. **前後端通訊**：前端使用 ComfyUI 的 `api.fetchApi()` 而非原生 `fetch()`。API key 由前端讀取後在每次 request body 中傳給後端。

6. **現有程式碼架構分析**：目前的核心邏輯已經良好分離 — `CivitaiAPI`（純 API client）、`extract_metadata()`（純資料轉換）、`resolve_resource()`（純解析邏輯）都可以直接被 API endpoint 呼叫。主要工作是建立 API layer wrapper 和前端 UI。
