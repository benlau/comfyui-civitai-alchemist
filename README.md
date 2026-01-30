# ComfyUI Civitai Alchemist

貼上 Civitai 圖片網址，自動取得生成參數、下載所需模型，並產生 ComfyUI workflow 來重現圖片。

## 功能

1. **取得 Metadata** — 從 Civitai 圖片頁面擷取 prompt、模型、LoRA、sampler 等生成參數
2. **解析模型** — 透過 hash/名稱查找模型的下載連結
3. **下載模型** — 自動下載 checkpoint、LoRA 等到 ComfyUI 對應目錄
4. **產生 Workflow** — 生成 ComfyUI API 格式的 workflow JSON，可直接送入執行

## 環境需求

- Python 3.10-3.12
- ComfyUI（已安裝在 `../ComfyUI`）
- uv 套件管理器

## 快速開始

### 1. 環境設定

```bash
bash scripts/setup.sh
```

### 2. 設定 API Key

```bash
cp .env.example .env
# 編輯 .env，填入你的 Civitai API key
```

API key 可從 [Civitai 帳號設定](https://civitai.com/user/account) 取得。

### 3. 一鍵重現圖片

```bash
# 完整 pipeline：取得 metadata → 解析模型 → 下載 → 產生 workflow
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/116872916

# 產生 workflow 後直接送到 ComfyUI 執行
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/116872916 --submit

# 跳過下載（模型已存在時）
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/116872916 --skip-download
```

### 4. 逐步執行（方便除錯）

每個步驟都會產生一個 JSON 檔案，可以獨立檢查：

```bash
# Step 1: 取得圖片 metadata
.venv/bin/python -m pipeline.fetch_metadata https://civitai.com/images/116872916
# 產出: output/metadata.json

# Step 2: 解析模型下載資訊
.venv/bin/python -m pipeline.resolve_models
# 產出: output/resources.json

# Step 3: 下載模型（先用 --dry-run 確認）
.venv/bin/python -m pipeline.download_models --dry-run
.venv/bin/python -m pipeline.download_models
# 產出: 模型檔案下載到 ComfyUI/models/ 對應目錄

# Step 4: 產生 workflow
.venv/bin/python -m pipeline.generate_workflow
# 產出: output/workflow.json

# Step 4b: 產生並送入 ComfyUI 執行
.venv/bin/python -m pipeline.generate_workflow --submit
```

## 專案結構

```
comfyui-civitai-alchemist/
├── pipeline/                   # 主要 pipeline 腳本
│   ├── fetch_metadata.py       # Step 1: URL → metadata.json
│   ├── resolve_models.py       # Step 2: metadata → resources.json
│   ├── download_models.py      # Step 3: 下載模型檔案
│   ├── generate_workflow.py    # Step 4: 產生 workflow.json
│   ├── sampler_map.py          # Civitai ↔ ComfyUI sampler 名稱對照
│   └── reproduce.py            # 一鍵完整 pipeline
├── utils/
│   ├── civitai_api.py          # Civitai API client
│   └── model_manager.py        # 模型下載與目錄管理
├── scripts/                    # 環境設定腳本
├── output/                     # Pipeline 輸出（gitignored）
│   ├── metadata.json
│   ├── resources.json
│   └── workflow.json
├── .env                        # 環境變數（gitignored）
├── .env.example                # .env 範本
└── pyproject.toml              # 專案依賴
```

## 目前支援範圍

- txt2img workflow（含 LoRA）
- 標準節點：CheckpointLoaderSimple、KSampler、CLIPTextEncode、EmptyLatentImage、VAEDecode、SaveImage、LoraLoader
- 使用 checkpoint 內建的 VAE

## 尚未支援

- img2img / inpainting
- ControlNet
- Hires fix / upscaling
- 自訂 VAE
- 非標準 ComfyUI 節點

## 參考資料

- [Civitai API Documentation](https://github.com/civitai/civitai/wiki/REST-API-Reference)
- [ComfyUI Custom Nodes Guide](https://docs.comfy.org/development/core-concepts/custom-nodes)

## License

MIT
