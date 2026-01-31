# ComfyUI Sidebar Extension 研究：Civitai Alchemist 整合方案

## 執行摘要

本研究針對將現有的 CLI pipeline 轉換為 ComfyUI 原生 sidebar extension 進行技術分析。目前 Civitai Alchemist 是一個 4 步驟的命令列工具，使用者需要在終端機操作。我們的目標是將其整合為 ComfyUI 左側面板的一個 sidebar tab，讓使用者可以直接在 ComfyUI UI 內輸入 Civitai image ID、查看圖片資訊、下載缺少的 model，並一鍵產生 workflow。

關鍵發現：

- ComfyUI 的新前端（Vue 3 + PrimeVue）提供了完整的 `extensionManager.registerSidebarTab()` API，可以在左側面板新增自定義 tab
- 後端透過 aiohttp 的 `PromptServer.instance.routes` 可以註冊自定義 API endpoint，前端透過 `api.fetchApi()` 呼叫
- 前端選擇 Vue 3 + TypeScript 與 ComfyUI 原生前端一致，可以直接使用 PrimeVue 元件
- Civitai API Key 透過 ComfyUI 內建的 Settings 系統管理，符合社群慣例
- 計畫發佈到 ComfyUI Registry，需要在 `pyproject.toml` 加入 `[tool.comfy]` 區段

## 背景與脈絡

Civitai Alchemist 目前是一個純 Python CLI 工具，透過 4 個步驟（fetch metadata → resolve models → download models → generate workflow）從 Civitai image URL 重建圖片生成環境。雖然功能完整，但使用者需要切換到終端機操作，體驗不夠流暢。

ComfyUI 的新前端架構（v1.2.4+）基於 Vue 3 + TypeScript + PrimeVue，提供了 Extension API 讓第三方套件可以註冊 sidebar tab、bottom panel、menu item 等 UI 元件。這讓我們有機會將整個 pipeline 的操作介面直接嵌入 ComfyUI，實現「貼上 image ID → 查看資訊 → 下載 model → 產生 workflow」的一站式體驗。

## UI 設計

### 主要介面流程

使用者在 ComfyUI 左側 sidebar 會看到一個 Civitai Alchemist 的 icon，點選後展開面板。整個操作流程分為 3 個階段：輸入 → 資訊展示與下載 → 產生 workflow。

### API Key 管理

Civitai API Key 的存放採用 ComfyUI 內建的 Settings 系統，這是社群的標準做法（例如 ComfyUI-Civitai-Toolkit 也是如此）。使用者透過 ComfyUI 的 Settings 面板（`Ctrl + ,`）設定 API key，而非在 sidebar 裡另外做設定頁。

API key 的註冊方式是在 `app.registerExtension()` 中宣告 `settings` 欄位。ComfyUI 會自動在 Settings 面板產生對應的輸入欄位，並持久化到 `ComfyUI/user/default/comfy.settings.json`。

```typescript
// 在 main.ts 中註冊
window.app.registerExtension({
  name: 'civitai-alchemist',
  settings: [{
    id: 'civitai-alchemist.api_key',
    name: 'Civitai API Key',
    type: 'text',
    defaultValue: '',
    tooltip: 'Generate at https://civitai.com/user/account',
    attrs: {
      type: 'password',       // 遮罩顯示
      placeholder: 'sk_...'
    }
  }]
})
```

前端在需要時透過 `app.extensionManager.setting.get('civitai-alchemist.api_key')` 讀取，並在 API request 中傳給後端。Sidebar 本身不需要設定頁，但在 API key 未設定時會顯示提示訊息引導使用者。

### ASCII UI Mockup

#### 階段 0：API Key 未設定

當使用者第一次開啟 sidebar 且尚未設定 API key 時，顯示提示：

```
┌─────────────────────────────────┐
│  ⚗ Civitai Alchemist            │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐   │
│  │ ⚠ Civitai API Key not   │   │
│  │   configured.            │   │
│  │                          │   │
│  │ Go to Settings (Ctrl+,) │   │
│  │ → Civitai Alchemist      │   │
│  │ to set your API key.     │   │
│  │                          │   │
│  │ ┌──────────────────────┐ │   │
│  │ │  Open Settings       │ │   │
│  │ └──────────────────────┘ │   │
│  └─────────────────────────┘   │
│                                 │
│  Image ID or URL                │
│  ┌───────────────────────┬────┐ │
│  │                       │ Go │ │
│  └───────────────────────┴────┘ │
│  (disabled until API key is set)│
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
└─────────────────────────────────┘
```

#### 階段 1：初始狀態 — 輸入 Image ID

API key 已設定，正常使用狀態：

```
┌─────────────────────────────────┐
│  ⚗ Civitai Alchemist            │
├─────────────────────────────────┤
│                                 │
│  Image ID or URL                │
│  ┌───────────────────────┬────┐ │
│  │ 116872916             │ Go │ │
│  └───────────────────────┴────┘ │
│                                 │
│  Paste a Civitai image ID or    │
│  URL to get started.            │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
└─────────────────────────────────┘
```

#### 階段 2：載入中

```
┌─────────────────────────────────┐
│  ⚗ Civitai Alchemist            │
├─────────────────────────────────┤
│                                 │
│  Image ID or URL                │
│  ┌───────────────────────┬────┐ │
│  │ 116872916             │ Go │ │
│  └───────────────────────┴────┘ │
│                                 │
│  ┌─────────────────────────┐   │
│  │ ░░░░░░░░░░░░░░░        │   │
│  │ Fetching metadata...    │   │
│  └─────────────────────────┘   │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
│                                 │
└─────────────────────────────────┘
```

#### 階段 3：資訊展示 + Model 下載

```
┌─────────────────────────────────┐
│  ⚗ Civitai Alchemist            │
├─────────────────────────────────┤
│                                 │
│  Image ID or URL                │
│  ┌───────────────────────┬────┐ │
│  │ 116872916             │ Go │ │
│  └───────────────────────┴────┘ │
│                                 │
│  ── Generation Info ──────────  │
│  Prompt:                        │
│  masterpiece, best quality,     │
│  1girl, long hair, ...          │
│                                 │
│  Sampler: DPM++ 2M Karras       │
│  Steps: 30  CFG: 7  Seed: 1234 │
│  Size: 512×768                  │
│  Clip Skip: 2                   │
│                                 │
│  ── Models (4) ───────────────  │
│                                 │
│  ┌─────────────────────────┐   │
│  │ ✅ Beautiful Realistic   │   │
│  │    Checkpoint · 2.1 GB   │   │
│  │    Found in: checkpoints │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │ ❌ Detail Tweaker        │   │
│  │    LoRA · 144 MB         │   │
│  │    ┌──────────────────┐  │   │
│  │    │   ⬇ Download     │  │   │
│  │    └──────────────────┘  │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │ ❌ epiCPhotoGasm        │   │
│  │    LoRA · 56 MB          │   │
│  │    ┌──────────────────┐  │   │
│  │    │   ⬇ Download     │  │   │
│  │    └──────────────────┘  │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │ ✅ kl-f8-anime2         │   │
│  │    VAE · 335 MB          │   │
│  │    Found in: vae         │   │
│  └─────────────────────────┘   │
│                                 │
│  Missing: 2 of 4               │
│  ┌─────────────────────────┐   │
│  │   ⬇ Download All (2)    │   │
│  └─────────────────────────┘   │
│                                 │
│  ── Generate ─────────────────  │
│  ┌─────────────────────────┐   │
│  │  ▶ Generate Workflow     │   │
│  └─────────────────────────┘   │
│                                 │
└─────────────────────────────────┘
```

#### 階段 4：下載中狀態

```
  ┌─────────────────────────────┐
  │ ⏳ Detail Tweaker            │
  │    LoRA · 144 MB             │
  │    ░░░░░░░░░░░░░░░  67%     │
  │    96 MB / 144 MB            │
  └─────────────────────────────┘
```

#### 階段 5：Workflow 產生完成

```
│  ── Generate ─────────────────  │
│  ┌─────────────────────────┐   │
│  │  ✅ Workflow Generated   │   │
│  │  Loaded to canvas.       │   │
│  │  Saved to workflows.     │   │
│  └─────────────────────────┘   │
```

### UI 設計說明

面板的設計遵循 ComfyUI sidebar 的慣例，寬度約 300px，內容可捲動。主要設計考量：

- **輸入區域**固定在最上方，隨時可以更換 image ID
- **Generation Info** 展示關鍵的生成參數，prompt 可摺疊（避免太長佔據空間）
- **Models 列表**每個 model 用卡片呈現，用 ✅/❌ 標示是否已存在
- 已存在的 model 顯示路徑，缺少的 model 顯示下載按鈕和檔案大小
- **Download All** 按鈕只在有缺少 model 時出現
- **Generate Workflow** 按鈕在所有 model 都就緒後會特別醒目

## 技術架構

### 整體架構圖

```
┌─────────────────────────────────────────────────────────┐
│                    ComfyUI Browser                       │
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────────┐ │
│  │   Sidebar Panel      │  │     Canvas (workflow)     │ │
│  │   (Vue 3 + TS)       │  │                          │ │
│  │                      │  │   app.loadGraphData()    │ │
│  │   ┌──────────────┐   │  │          ↑               │ │
│  │   │  App.vue     │   │  └──────────┼───────────────┘ │
│  │   │  components/ │   │             │                  │
│  │   └──────┬───────┘   │             │                  │
│  └──────────┼───────────┘             │                  │
│             │ api.fetchApi()          │                   │
│             ↓                         │                   │
├─────────────────────────────────────────────────────────┤
│                    ComfyUI Server                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ComfyUI Settings (comfy.settings.json)           │   │
│  │  civitai-alchemist.api_key → Civitai API Key      │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Custom API Routes (aiohttp)                      │   │
│  │  POST /civitai/fetch     → fetch_metadata         │   │
│  │  POST /civitai/resolve   → resolve_models         │   │
│  │  POST /civitai/download  → download (single)      │   │
│  │  POST /civitai/download-all → download (batch)    │   │
│  │  POST /civitai/generate  → generate_workflow      │   │
│  │  GET  /civitai/status    → pipeline status        │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────┼───────────────────────────┐   │
│  │  Pipeline (existing Python code)                  │   │
│  │  fetch_metadata → resolve_models → download →     │   │
│  │  generate_workflow                                │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  WebSocket (PromptServer.send_sync)               │   │
│  │  civitai.progress → download progress updates     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 前端架構（Vue 3 + TypeScript）

前端使用 Vue 3 + TypeScript + PrimeVue，透過 Vite 建置後輸出到 `js/` 目錄。ComfyUI 會自動載入 `WEB_DIRECTORY` 指定目錄中的所有 `.js` 檔案。

**技術選型理由：**

選擇 Vue 3 而非 Plain JS 或 React，主要因為 ComfyUI 的原生前端就是 Vue 3 + PrimeVue。這意味著我們可以直接使用 PrimeVue 的 UI 元件（Button、InputText、ProgressBar、Card 等），讓 sidebar 的視覺風格與 ComfyUI 原生 UI 一致。此外，Vue 3 的 Composition API 配合 TypeScript 提供良好的型別安全性和程式碼組織。

**前端檔案結構：**

```
ui/
├── src/
│   ├── main.ts                 # Entry: 等待 app 初始化，註冊 sidebar tab
│   ├── App.vue                 # Root component: 管理整體狀態和流程
│   ├── composables/
│   │   ├── useCivitaiApi.ts    # 封裝後端 API 呼叫
│   │   └── useDownload.ts      # 下載狀態管理 + WebSocket 監聽
│   ├── components/
│   │   ├── ImageInput.vue      # Image ID/URL 輸入區域
│   │   ├── GenerationInfo.vue  # 生成參數展示（prompt, sampler, steps...）
│   │   ├── ModelList.vue       # Model 列表容器
│   │   ├── ModelCard.vue       # 單一 model 卡片（狀態、下載按鈕、進度條）
│   │   └── WorkflowActions.vue # Generate Workflow 按鈕和結果顯示
│   └── types/
│       └── index.ts            # TypeScript 型別定義
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tsconfig.node.json
```

**Sidebar 與 Settings 註冊方式（`main.ts`）：**

```typescript
import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import App from './App.vue'

async function init() {
  // 等待 ComfyUI app 物件可用
  while (!window.app?.extensionManager) {
    await new Promise(r => setTimeout(r, 50))
  }

  // 註冊 Settings（API Key 欄位）
  window.app.registerExtension({
    name: 'civitai-alchemist',
    settings: [{
      id: 'civitai-alchemist.api_key',
      name: 'Civitai API Key',
      type: 'text',
      defaultValue: '',
      tooltip: 'Generate at https://civitai.com/user/account',
      attrs: {
        type: 'password',
        placeholder: 'sk_...'
      }
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

void init()
```

在 Vue 元件中讀取 API key：

```typescript
// composables/useCivitaiApi.ts
function getApiKey(): string {
  return window.app.extensionManager.setting.get('civitai-alchemist.api_key') || ''
}

// API 呼叫時帶上 api_key
async function fetchMetadata(imageId: string) {
  const response = await api.fetchApi('/civitai/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_id: imageId,
      api_key: getApiKey()
    })
  })
  return response.json()
}
```

**Vite 建置設定（`vite.config.ts`）：**

Vite 使用 library mode 建置，輸出 ES module 格式到 `js/` 目錄。ComfyUI 的 `app.js` 被設為 external，在執行時從 ComfyUI server 載入而不是打包進去。

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

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

### 後端架構（Python API Routes）

後端在 `__init__.py` 中註冊自定義 API routes，這些 routes 呼叫現有的 pipeline 程式碼。關鍵設計是將現有的 pipeline 函式拆分為可獨立呼叫的 API，而非一次性執行整個 pipeline。

**API Endpoints 設計：**

所有需要呼叫 Civitai API 的 endpoint 都接受 `api_key` 參數（由前端從 ComfyUI Settings 讀取後帶入）。

| Endpoint | Method | 用途 | 回傳 |
|----------|--------|------|------|
| `/civitai/fetch` | POST | 輸入 image ID/URL + api_key，取得 metadata | 圖片 metadata + 生成參數 |
| `/civitai/resolve` | POST | 根據 metadata + api_key 解析 model 資訊 | model 列表（含是否已存在、下載 URL、檔案大小） |
| `/civitai/download` | POST | 下載單一 model（需 api_key） | 開始下載，透過 WebSocket 回報進度 |
| `/civitai/download-all` | POST | 下載所有缺少的 model（需 api_key） | 批次下載，透過 WebSocket 回報進度 |
| `/civitai/generate` | POST | 產生 workflow JSON | API-format workflow JSON（不需 api_key） |

**進度回報機制：**

下載進度透過 ComfyUI 內建的 WebSocket 機制回報。後端使用 `PromptServer.instance.send_sync()` 發送自定義事件，前端透過 `api.addEventListener()` 監聽：

```python
# 後端發送進度
PromptServer.instance.send_sync("civitai.download.progress", {
    "model_name": "Detail Tweaker",
    "progress": 67,
    "downloaded": 96_000_000,
    "total": 144_000_000
})
```

```typescript
// 前端監聽進度
api.addEventListener("civitai.download.progress", (event) => {
  const { model_name, progress, downloaded, total } = event.detail
  // 更新對應 model 的進度條
})
```

### 前後端互動流程

完整的使用者操作流程如下。前端在每次 API 呼叫時會從 ComfyUI Settings 讀取 API key 並帶入 request body，後端使用該 key 呼叫 Civitai API。

```
使用者開啟 sidebar
        │
        ├─ 檢查 Settings 中 API key 是否已設定
        │  ├─ 未設定 → 顯示提示訊息 + Open Settings 按鈕
        │  └─ 已設定 → 顯示正常輸入介面
        │
        ▼
使用者輸入 Image ID → 點擊 Go
        │
        ▼
前端 POST /civitai/fetch { image_id: "116872916", api_key: "sk_..." }
        │
        ▼
後端呼叫 fetch_metadata.extract_metadata()
        │  回傳: metadata (prompt, sampler, steps, resources...)
        ▼
前端 POST /civitai/resolve { metadata }
        │
        ▼
後端呼叫 resolve_models + model_manager.find_model()
        │  回傳: resources[] (每個 model 的 name, type, size,
        │         download_url, exists, local_path)
        ▼
前端顯示 Generation Info + Model 列表
        │
        ├─ 使用者點「Download」(單一)
        │  → POST /civitai/download { resource }
        │  → WebSocket: civitai.download.progress
        │  → 下載完成後更新 model 狀態為 ✅
        │
        ├─ 使用者點「Download All」
        │  → POST /civitai/download-all { resources }
        │  → WebSocket: civitai.download.progress (逐一)
        │  → 全部完成後更新所有 model 狀態
        │
        ▼
使用者點「Generate Workflow」
        │
        ▼
前端 POST /civitai/generate { metadata, resources }
        │
        ▼
後端呼叫 generate_workflow.build_workflow()
        │  回傳: workflow JSON (API-format)
        ▼
前端執行兩件事：
  1. app.loadGraphData(workflow) → 在 canvas 上顯示
  2. api.fetchApi("/userdata/workflows/civitai_XXXXX.json",
       { method: "POST", body: workflow })
     → 儲存到 workflow library
```

### Pipeline 程式碼重構

現有的 pipeline 模組是以 CLI script 設計的（讀寫 `output/` 目錄的 JSON 檔案）。轉換為 API 後端時，需要做以下調整：

1. **抽出核心邏輯為可呼叫函式：** 目前 `fetch_metadata.py` 的核心邏輯在 `main()` 裡面跟 argparse、file I/O 混在一起。需要把核心邏輯抽出為獨立函式（例如 `extract_metadata(image_id) -> dict`），讓 API route handler 可以直接呼叫。

2. **資料透過參數傳遞而非檔案：** 目前 step 之間透過 `output/metadata.json` 等檔案串接。API 模式下改為直接在記憶體中傳遞 dict 物件。

3. **下載進度回調：** `model_manager.download_file()` 目前用 tqdm 顯示進度。需要加入 callback 機制，讓 API 可以透過 WebSocket 回報進度。

好消息是，目前程式碼的分層已經做得不錯：`CivitaiAPI`、`ModelManager`、`sampler_map` 等都是獨立的工具類，重構量不大。主要是把各個 `main()` 函式中的核心邏輯抽出來。

## 專案結構

### 重構後的完整專案結構

```
comfyui-civitai-alchemist/
├── __init__.py                  # ComfyUI entry: WEB_DIRECTORY + API routes
├── pyproject.toml               # 加入 [tool.comfy] for Registry
│
├── api/                         # NEW: API route handlers
│   ├── __init__.py
│   └── routes.py                # aiohttp route handlers
│
├── pipeline/                    # 現有 pipeline (重構核心函式)
│   ├── fetch_metadata.py        # extract_metadata(image_id) → dict
│   ├── resolve_models.py        # resolve(metadata) → resources[]
│   ├── download_models.py       # download(resource, callback) → path
│   ├── generate_workflow.py     # build_workflow(metadata, resources) → dict
│   ├── sampler_map.py           # 不變
│   └── reproduce.py             # CLI entry point (保留給 CLI 使用)
│
├── utils/                       # 現有 utils
│   ├── civitai_api.py           # 不變
│   └── model_manager.py         # 加入 progress callback 支援
│
├── ui/                          # NEW: Vue 3 frontend source
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── composables/
│   │   │   ├── useCivitaiApi.ts
│   │   │   └── useDownload.ts
│   │   ├── components/
│   │   │   ├── ImageInput.vue
│   │   │   ├── GenerationInfo.vue
│   │   │   ├── ModelList.vue
│   │   │   ├── ModelCard.vue
│   │   │   └── WorkflowActions.vue
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── js/                          # BUILD OUTPUT: Vite compiled JS
│   ├── main.js                  # sidebar entry point
│   └── assets/                  # chunked vendor files
│
├── nodes/                       # ComfyUI custom nodes (未來擴充)
│   └── __init__.py
│
├── scripts/                     # 現有 scripts
├── docs/                        # 文件
├── .github/
│   └── workflows/
│       └── publish.yml          # NEW: Registry 自動發佈
└── output/                      # CLI 模式的輸出 (gitignored)
```

### `__init__.py` 改動

根入口需要同時處理 ComfyUI node registration、web directory 和 API route registration：

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

### `api/routes.py` 範例結構

```python
from aiohttp import web
from server import PromptServer

def register_routes(server_instance: PromptServer):
    @server_instance.routes.post("/civitai/fetch")
    async def fetch_metadata(request):
        data = await request.json()
        image_id = data["image_id"]
        # call pipeline.fetch_metadata core function
        metadata = extract_metadata(image_id)
        return web.json_response(metadata)

    @server_instance.routes.post("/civitai/resolve")
    async def resolve_models(request):
        data = await request.json()
        # call pipeline.resolve_models core function
        resources = resolve(data["metadata"])
        return web.json_response(resources)

    @server_instance.routes.post("/civitai/download")
    async def download_model(request):
        data = await request.json()
        resource = data["resource"]
        # download with progress callback via WebSocket
        async def progress_callback(downloaded, total):
            server_instance.send_sync("civitai.download.progress", {
                "model_name": resource["name"],
                "downloaded": downloaded,
                "total": total
            })
        await download_with_callback(resource, progress_callback)
        return web.json_response({"status": "ok"})

    @server_instance.routes.post("/civitai/generate")
    async def generate_workflow(request):
        data = await request.json()
        workflow = build_workflow(data["metadata"], data["resources"])
        return web.json_response(workflow)
```

### pyproject.toml 重構

目前的 `pyproject.toml` 是為了 CLI 工具 + 從零架設 ComfyUI 開發環境而設計的。轉換為 custom node 後需要大幅調整，讓相依性更合理。

**目前的問題：**

1. **`[project.optional-dependencies].dev` 列的都是 ComfyUI 本身的相依性**（torch, torchvision, aiohttp, numpy, pillow, scipy, psutil, pyyaml, einops, transformers, tokenizers, sentencepiece, safetensors, alembic, sqlalchemy, av, etc.）。這些是當初為了架設完整的 ComfyUI 開發環境加的，但作為 custom node，這些全部由 ComfyUI runtime 提供，不該列為相依性。
2. **`python-dotenv`** — CLI 模式下讀 `.env` 用的。Custom node 模式下 API key 改用 ComfyUI Settings 系統，models dir 由 ComfyUI 提供，不再需要。但 CLI 模式仍需要。
3. **`tqdm`** — CLI 模式下載進度條用的。Custom node 模式下改用 WebSocket 回報進度。不過 ComfyUI 本身也有 tqdm，列著也無害。
4. **`[[tool.uv.index]]` 和 `[tool.uv.sources]`** — 本地開發用的 PyTorch CUDA index 設定，跟 custom node 發佈無關。
5. **缺少 `[tool.comfy]`** — Registry 發佈必要的區段。
6. **缺少 `[project.urls]`** 和 `license`。

**ComfyUI runtime 已提供的套件（不需要列為相依性）：**

根據 ComfyUI 的 [dependencies 文件](https://docs.comfy.org/development/core-concepts/dependencies)，以下套件由 ComfyUI 提供：

| 套件 | 版本 | 說明 |
|------|------|------|
| torch, torchvision, torchaudio | 2.4+ | GPU 推理 |
| aiohttp | >=3.11.8 | HTTP server（PromptServer 用的） |
| numpy | >=1.25.0 | 數值計算 |
| PIL/Pillow | - | 影像處理 |
| scipy | - | 科學計算 |
| tqdm | - | 進度條 |
| psutil | - | 系統資訊 |
| pyyaml | - | YAML 解析 |
| einops | - | Tensor 操作 |
| transformers, tokenizers, sentencepiece | - | NLP 模型 |
| safetensors | >=0.4.2 | 模型讀寫 |
| torchsde | - | SDE 求解 |
| alembic, sqlalchemy | - | 資料庫 |

**建議的新 pyproject.toml：**

```toml
[project]
name = "comfyui-civitai-alchemist"
description = "Reproduce Civitai images locally via ComfyUI"
version = "0.1.0"
license = { file = "LICENSE" }
requires-python = ">=3.10,<3.13"

# Custom node 的 runtime 相依性
# 只列 ComfyUI 本身「沒有」提供的套件
dependencies = [
    "requests>=2.31.0",
]

[project.optional-dependencies]
# CLI 模式額外需要的套件（非 custom node 使用者不需要）
cli = [
    "tqdm",
    "python-dotenv",
]

[project.urls]
Repository = "https://gitlab.com/purefern5078/comfyui-civitai-alchemist"

[tool.comfy]
PublisherId = "purefern5078"
DisplayName = "Civitai Alchemist"
Icon = ""
includes = ["js/"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["."]
```

**改動說明：**

- **`dependencies`** 只剩 `requests`。這是 ComfyUI 沒有提供的，用來呼叫 Civitai REST API。
- **`python-dotenv` 和 `tqdm`** 移到 `[project.optional-dependencies].cli`。CLI 使用者可以 `pip install .[cli]` 安裝。Custom node 模式下不需要（API key 用 Settings、進度用 WebSocket、models dir 由 ComfyUI 提供）。
- **移除整個 `dev` optional-dependencies**。那些是 ComfyUI runtime 套件，不該由 custom node 安裝。
- **移除 `[[tool.uv.index]]` 和 `[tool.uv.sources]]`** 的 PyTorch CUDA index 設定。這些只在本地從零架設 ComfyUI 時需要，跟 custom node 無關。如果本地開發仍需要，可以放在 `uv.toml` 或開發文件中說明。
- **新增 `[tool.comfy]`** 區段。`includes = ["js/"]` 確保 Registry 打包時包含建置後的前端 JS，即使 `js/` 在 `.gitignore` 中。
- **新增 `license` 和 `[project.urls]`**。

**CLI 使用者的安裝方式改變：**

```bash
# 之前（安裝完整開發環境）
pip install -e ".[dev]"

# 之後（只安裝 CLI 工具）
pip install -e ".[cli]"

# Custom node 使用者（透過 ComfyUI Manager 安裝）
# 只需要 requests，由 Registry 自動處理
```

**注意：** Pipeline 程式碼中 `import tqdm` 和 `from dotenv import load_dotenv` 需要加上條件判斷或 try/except，讓 custom node 模式下可以正常運作：

```python
# utils/model_manager.py
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None  # custom node 模式下不用 tqdm

# pipeline/reproduce.py (CLI entry point)
# CLI 才需要 load_dotenv，API routes 不需要
```

### GitHub Actions 發佈流程

```yaml
# .github/workflows/publish.yml
name: Build and Publish to Comfy Registry
on:
  workflow_dispatch:
  push:
    branches: [main]
    paths: [pyproject.toml]

jobs:
  publish:
    runs-on: ubuntu-latest
    if: github.repository == 'purefern5078/comfyui-civitai-alchemist'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Build frontend
        working-directory: ui
        run: |
          npm install
          npm run build
      - uses: Comfy-Org/publish-node-action@v1
        with:
          personal_access_token: ${{ secrets.REGISTRY_ACCESS_TOKEN }}
```

## 解決方案評估

### 方案比較：Plain JS vs Vue 3 vs React

我們已決定使用 Vue 3 + TypeScript，以下是這個選擇的技術評估：

**Vue 3 + TypeScript 的優勢：**
- 與 ComfyUI 前端技術棧一致（Vue 3 + PrimeVue），可以使用相同的 UI 元件和設計語言
- PrimeVue 提供豐富的現成元件：Button, InputText, ProgressBar, Card, Accordion, Tag 等，省去自行設計 UI 的時間
- Vue 3 的 Composition API (`ref`, `computed`, `watch`) 配合 TypeScript 提供良好的型別安全性
- Vite 作為建置工具，Hot Module Replacement 開發體驗佳

**需要注意的地方：**
- 需要 build step（`npm run build`），開發時需要先建置才能在 ComfyUI 中看到效果
- PrimeVue 會被打包進 JS output，可能增加 bundle size（但 sidebar extension 可接受）
- 需要處理 ComfyUI app 物件的初始化時機（等待 `window.app` 可用）

### 風險與對策

| 風險 | 影響 | 對策 |
|------|------|------|
| `app.loadGraphData()` 對 API-format JSON 的支援度 | canvas 可能無法正確顯示 | 先測試確認，必要時改用 `/prompt` 直接執行 |
| 下載大型 model 時 async/await 阻塞 | ComfyUI server 無回應 | 使用 asyncio.to_thread() 在背景執行下載 |
| Civitai API rate limiting | 連續操作可能被限流 | 現有 retry/backoff 機制已能處理 |
| Vue/PrimeVue 版本與 ComfyUI 前端不一致 | 樣式衝突或元件行為差異 | 獨立打包 PrimeVue，使用 scoped styles |

## 建議與下一步

基於分析結果，建議的實作順序如下：

**第一階段：基礎框架建立**
- 建立 `ui/` 目錄和 Vue 3 + Vite 專案
- 建立 `api/routes.py` 基本架構
- 修改 `__init__.py` 註冊 WEB_DIRECTORY 和 API routes
- 實作 sidebar tab 註冊和空白面板顯示

**第二階段：核心功能串接**
- 重構 pipeline 模組，抽出核心函式
- 實作 `/civitai/fetch` 和 `/civitai/resolve` endpoints
- 前端 Image Input + Generation Info + Model List 元件
- Model 存在/缺少狀態檢查

**第三階段：下載功能**
- 實作 `/civitai/download` 和 `/civitai/download-all`
- `model_manager.py` 加入 progress callback
- WebSocket 進度回報
- 前端下載進度條

**第四階段：Workflow 產生**
- 實作 `/civitai/generate` endpoint
- 前端呼叫 `app.loadGraphData()` 載入 canvas
- 儲存到 workflow library (`/userdata/workflows/`)

**第五階段：發佈準備**
- 更新 `pyproject.toml` 的 `[tool.comfy]` 區段
- 建立 GitHub Actions publish workflow
- 註冊 ComfyUI Registry publisher account
- 測試安裝流程

如果研究結果符合預期，建議撰寫 PRD 來定義詳細的功能規格和驗收標準，然後根據 PRD 建立實作任務清單。

## 參考資料

### ComfyUI Extension 開發
- [Sidebar Tabs API](https://docs.comfy.org/custom-nodes/js/javascript_sidebar_tabs) — 官方 sidebar tab 註冊文件
- [Extension Settings API](https://docs.comfy.org/custom-nodes/js/javascript_settings) — Settings 欄位註冊文件
- [JavaScript Extensions Overview](https://docs.comfy.org/custom-nodes/js/javascript_overview) — 前端 extension 總覽
- [ComfyUI Server Routes](https://docs.comfy.org/development/comfyui-server/comms_routes) — 後端 API 路由文件
- [ComfyUI_frontend_vue_basic](https://github.com/jtydhr88/ComfyUI_frontend_vue_basic) — Vue 3 extension 範例
- [ComfyUI-React-Extension-Template](https://github.com/Comfy-Org/ComfyUI-React-Extension-Template) — React extension template（架構參考）
- [ComfyUI_frontend](https://github.com/Comfy-Org/ComfyUI_frontend) — ComfyUI 原生前端原始碼

### ComfyUI Registry
- [ComfyUI Dependencies](https://docs.comfy.org/development/core-concepts/dependencies) — ComfyUI runtime 提供的套件列表
- [pyproject.toml Specification](https://docs.comfy.org/registry/specifications) — Registry 規格
- [Publishing Nodes](https://docs.comfy.org/registry/publishing) — 發佈流程
- [Registry Standards](https://docs.comfy.org/registry/standards) — 安全標準
- [publish-node-action](https://github.com/Comfy-Org/publish-node-action) — GitHub Actions 發佈工具

### PrimeVue
- [PrimeVue Icons](https://primevue.org/icons/#list) — 可用圖示列表
- [PrimeVue Components](https://primevue.org/) — UI 元件文件
