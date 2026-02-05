# CLAUDE.md - Development Context

This file provides context for AI assistants (like Claude) working on this project.

## Project Overview

**ComfyUI Civitai Alchemist** reproduces Civitai images locally via ComfyUI. It works in two modes:

1. **ComfyUI Sidebar Extension** — A sidebar tab in ComfyUI's UI for the full reproduction workflow: query metadata, check model availability, download missing models, and generate a ComfyUI workflow — all without leaving the ComfyUI interface.
2. **CLI Pipeline** — A standalone 4-step pipeline that fetches metadata, resolves models, downloads them, and generates a ComfyUI workflow.

## Environment Information

### Windows (Native)

- **Hardware**: NVIDIA GeForce RTX 5090 Laptop GPU
- **CUDA Version**: 13.0 (PyTorch cu130)
- **Driver Version**: 581.29
- **OS**: Windows 11
- **Python**: 3.12.10
- **Package Manager**: uv 0.9.27
- **Models directory**: `../ComfyUI/models` (default; configurable via `MODELS_DIR` env var or `--models-dir` flag)
- **Limitations**: `triton` and `sageattention` are not available on native Windows

### WSL2 (Linux)

- **Hardware**: NVIDIA GeForce RTX 5090 (24GB VRAM)
- **CUDA Version**: 13.0
- **Driver Version**: 581.29
- **OS**: Ubuntu on WSL2
- **Python**: 3.12.3
- **Package Manager**: uv 0.9.27
- **Models directory**: `../ComfyUI/models` (default; configurable via `MODELS_DIR` env var or `--models-dir` flag)

## Pipeline Usage

The project is a 4-step pipeline, each step producing a JSON file:

```
URL → fetch_metadata → metadata.json
       resolve_models → resources.json
       download_models → files on disk
       generate_workflow → workflow.json → (optional) submit to ComfyUI
```

### One-shot (recommended)

```bash
# Full pipeline: fetch → resolve → download → generate workflow
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX

# Generate and submit to running ComfyUI
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX --submit

# Skip download (models already exist)
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX --skip-download

# Debug mode: run pipeline without downloading/submitting, save diagnostic report
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX --debug
```

### Step by step (for debugging)

```bash
# Step 1: Fetch metadata from Civitai
.venv/bin/python -m pipeline.fetch_metadata https://civitai.com/images/XXXXX

# Step 2: Resolve model download URLs
.venv/bin/python -m pipeline.resolve_models

# Step 3: Download models (use --dry-run to preview)
.venv/bin/python -m pipeline.download_models --dry-run
.venv/bin/python -m pipeline.download_models

# Step 4: Generate ComfyUI workflow
.venv/bin/python -m pipeline.generate_workflow

# Step 4b: Generate and submit to ComfyUI
.venv/bin/python -m pipeline.generate_workflow --submit
```

### Output files

All pipeline output goes to `output/` (gitignored):
- `output/metadata.json` — image generation parameters
- `output/resources.json` — resolved model download info
- `output/workflow.json` — ComfyUI API-format workflow
- `output/debug_report.json` — compact debug summary (~8KB, for AI/human review; `--debug` only)
- `output/debug_report_full.json` — complete debug data with raw API responses (~300KB+; `--debug` only)

Generated images from ComfyUI go to `../ComfyUI/output/`.

## Project Structure

```
comfyui-civitai-alchemist/
├── __init__.py                 # ComfyUI extension entry point (WEB_DIRECTORY, route registration)
├── civitai_routes.py           # Backend API routes (fetch, resolve, download, generate)
├── civitai_utils/              # Shared utilities (renamed from utils/ to avoid ComfyUI conflict)
│   ├── civitai_api.py          # Civitai REST API client (with retry/backoff)
│   └── model_manager.py        # Model download & directory management
├── pipeline/                   # CLI pipeline scripts
│   ├── fetch_metadata.py       # Step 1: URL → metadata.json
│   ├── resolve_models.py       # Step 2: metadata → resources.json
│   ├── download_models.py      # Step 3: download model files
│   ├── generate_workflow.py    # Step 4: generate workflow.json
│   ├── sampler_map.py          # Civitai ↔ ComfyUI sampler name mapping
│   ├── reproduce.py            # One-shot runner (all steps)
│   └── debug.py                # Debug report utilities (--debug mode)
├── ui/                         # Frontend source (Vue 3 + TypeScript + PrimeVue)
│   ├── src/
│   │   ├── main.ts             # Extension entry: sidebar tab & settings registration
│   │   ├── App.vue             # Root component with state management
│   │   ├── components/         # UI components
│   │   │   ├── ApiKeyWarning.vue   # API key not configured warning
│   │   │   ├── ImageInput.vue      # Image ID/URL input + Go button
│   │   │   ├── GenerationInfo.vue  # Generation parameters display
│   │   │   ├── ModelList.vue       # Model list container with summary
│   │   │   └── ModelCard.vue       # Individual model status card
│   │   ├── composables/
│   │   │   └── useCivitaiApi.ts    # API client composable (fetch, resolve, download, generate)
│   │   └── types/
│   │       ├── index.ts            # TypeScript type definitions (Metadata, Resource, etc.)
│   │       └── comfyui.d.ts        # ComfyUI global type declarations (window.app)
│   ├── package.json
│   └── vite.config.ts          # Vite library mode config → ../js/
├── js/                         # Built frontend output (committed for distribution)
├── nodes/                      # ComfyUI custom nodes (currently unused)
├── scripts/                    # Environment setup scripts (Linux/WSL2)
│   ├── setup.sh                # One-click environment setup
│   ├── run_comfyui.sh          # Start ComfyUI
│   ├── check_env.sh            # Environment health check
│   ├── benchmark.sh            # Performance testing
│   └── link.sh / unlink.sh    # Symlink management
├── .env                        # Environment variables (gitignored)
├── .env.example                # Template for .env
├── pyproject.toml              # Project config (ComfyUI Registry compatible)
└── README.md                   # User documentation
```

## Key Implementation Details

### ComfyUI Extension Entry (`__init__.py`)

- `WEB_DIRECTORY = "./js"` — tells ComfyUI to load built frontend JS
- `from . import civitai_routes` — triggers route registration via decorators at import time
- No custom nodes registered (`NODE_CLASS_MAPPINGS = {}`)

### Backend API Routes (`civitai_routes.py`)

Six POST endpoints, all registered via `@server.PromptServer.instance.routes.post()` decorators (standard ComfyUI pattern):

- `POST /civitai/fetch` — accepts `{ image_id, api_key }`, returns metadata JSON
- `POST /civitai/resolve` — accepts `{ metadata, api_key }`, returns resources list with `exists` status
- `POST /civitai/download` — accepts `{ resource, api_key }`, starts async download, returns `{ task_id }`
- `POST /civitai/download-all` — accepts `{ resources, api_key }`, downloads sequentially, returns `{ task_id }`
- `POST /civitai/download-cancel` — accepts `{ task_id }` or `{ cancel_all: true }`, cancels download(s)
- `POST /civitai/generate` — accepts `{ metadata, resources }`, returns `{ workflow, workflow_type, node_count }`

Key implementation details:
- Uses `FolderPathsModelAdapter` to check model existence and determine download paths via ComfyUI's `folder_paths` API (respects `extra_model_paths.yaml` config)
- Downloads use `aiohttp.ClientSession` for non-blocking async HTTP (not `requests`, which would block the event loop)
- Download progress pushed via WebSocket: `PromptServer.instance.send_sync("civitai.download.progress", payload)` with status values: `downloading`, `verifying`, `completed`, `failed`, `cancelled`
- Downloads write to `.part` temp files, verify SHA256 hash, then rename to final filename
- Active downloads tracked in module-level `_active_downloads` dict with cancel support via `asyncio.Event`
- `civitai_utils/` was renamed from `utils/` to avoid collision with ComfyUI's own `utils` package in `sys.modules`

### Frontend Architecture (`ui/`)

- **Framework**: Vue 3 + TypeScript + PrimeVue, built with Vite in library mode
- **Entry point** (`main.ts`): Registers sidebar tab and API key setting via `window.app.registerExtension()` and `window.app.extensionManager.registerSidebarTab()`
- **API communication**: Uses `window.app.api.fetchApi()` (ComfyUI's built-in fetch wrapper); API key read from ComfyUI Settings via `window.app.extensionManager.setting.get()`
- **WebSocket events**: Listens for `civitai.download.progress` events via `window.app.api.addEventListener()` to update download progress in real-time
- **Workflow loading**: Uses `window.app.loadApiJson(workflow, filename)` to load generated workflows onto the canvas, followed by manual `computeSize()` + `setSize()` + `graph.arrange()` to fix node layout (ComfyUI's built-in arrange fails without prior size computation)
- **CSS strategy**: Uses ComfyUI's native CSS variables (`--fg-color`, `--descrip-text`, `--border-color`, `--comfy-input-bg`), NOT PrimeVue tokens (which don't switch with ComfyUI's dark theme)
- **CSS injection**: `vite-plugin-css-injected-by-js` injects CSS via JS at runtime (ComfyUI only loads `main.js`, not separate CSS files)
- **Build output**: `js/main.js` (single ES module), loaded by ComfyUI via `WEB_DIRECTORY`

### Frontend Build

```bash
cd ui
npm install        # Install dependencies
npm run build      # Build to ../js/
npm run dev        # Watch mode for development
```

### Civitai API (`civitai_utils/civitai_api.py`)

- `get_image_metadata(image_id)` — `GET /api/v1/images?imageId={id}`, returns first item
- `get_model_version_by_hash(hash)` — `GET /api/v1/model-versions/by-hash/{hash}`
- `search_models(query, limit)` — `GET /api/v1/models?query={query}&limit={limit}`
- `CivitaiAPI(api_key=...)` — constructor accepts explicit API key (used by sidebar routes)
- Retry logic: 3 retries with exponential backoff (1s, 2s, 4s)
- Rate limit handling: respects 429 Retry-After header
- In CLI mode, API key loaded from `CIVITAI_API_KEY` env var (via dotenv)

### Metadata Structure

Civitai API returns nested `meta.meta` — the outer `meta` has an `id` and a nested `meta` dict with actual generation params. `fetch_metadata.py` handles this with:
```python
if "meta" in meta and isinstance(meta["meta"], dict):
    meta = meta["meta"]
```

### Sampler Mapping (`pipeline/sampler_map.py`)

Civitai combines sampler+scheduler in one string (e.g. "DPM++ 2M Karras"). ComfyUI separates them. The mapper:
1. Strips scheduler suffix ("Karras", "Exponential") from the sampler string
2. Maps the base sampler name (e.g. "DPM++ 2M" → "dpmpp_2m")
3. Optionally overrides scheduler from Civitai's "Schedule type" field

### Workflow Generation (`pipeline/generate_workflow.py`)

Generates ComfyUI API-format workflow (JSON DAG):
- Node references use `["node_id", output_index]` format
- LoRA nodes are chained: each takes model/clip from the previous
- Custom VAE: if a VAE resource exists, a VAELoader node (node 9) is added; otherwise uses checkpoint's built-in VAE (output index 2)
- Embeddings: embedding filenames from resources are converted to `embedding:name` syntax in prompts (with fuzzy matching for names with optional spaces, e.g. "lazy pos" → "embedding:lazypos")
- SaveImage prefix: `civitai_{image_id}`

### Download Mechanism (`civitai_routes.py`)

- Async downloads using `aiohttp.ClientSession` — does not block ComfyUI's event loop
- Downloads write to `.part` temp file → SHA256 verification → rename to final filename
- Progress pushed via WebSocket every 500ms max: `PromptServer.instance.send_sync("civitai.download.progress", {...})`
- Active downloads tracked in `_active_downloads: Dict[str, DownloadTask]` with `asyncio.Event` for cancellation
- Civitai download URL authenticated via `?token={api_key}` query parameter
- Batch downloads execute sequentially (one model at a time), with failed models skipped automatically
- On Windows, `.part` file cleanup happens after the file handle is closed (outside `with open()` block) to avoid file locking issues

### Workflow Canvas Loading

- Frontend uses `window.app.loadApiJson(workflow, filename)` to load API-format workflow
- After loading, manually runs `computeSize()` + `setSize()` on all nodes, then `graph.arrange()` to fix layout
- This workaround is needed because `loadApiJson`'s built-in `arrange()` uses default node sizes (before `computeSize` runs), causing all nodes to stack at (10,10)
- Missing model warning dialog shown before generation if any models are not downloaded

### Debug Mode (`pipeline/debug.py`)

The `--debug` flag on `reproduce.py` runs the pipeline (fetch → resolve → generate) without downloading or submitting, while capturing all intermediate data for diagnosis:

- **Two-tier reports**: `debug_report.json` (compact summary ~8KB) and `debug_report_full.json` (complete data ~300KB+)
- **Summary stripping**: `_build_summary()` removes `response_body` from API calls, `raw_image_data` from fetch step, and `comfy` field from `raw_meta` (embedded ComfyUI workflow JSON string)
- **API call logging**: `CivitaiAPI` accepts optional `api_log: list` param; `_request()` appends method, url, status_code, elapsed_ms, response_size_bytes, and response_body for each call
- **Decision recording**: Pipeline functions accept optional `debug_data: dict` param to record enrichment source, resolve strategies, sampler mapping, and workflow type
- **Backward compatibility**: All debug params default to `None`; `pipeline/debug.py` is only imported when `--debug` is active (lazy import)
- **Error handling**: Partial debug report is saved before `sys.exit(1)` on any pipeline error

### Model Manager (`civitai_utils/model_manager.py`)

- `ModelManager(models_dir=)` accepts a models directory path; falls back to `MODELS_DIR` env var, then `../ComfyUI/models`
- `TYPE_MAPPING` maps Civitai type names to ComfyUI subdirectories
- `find_model()` searches recursively with `rglob`
- `download_file()` streams with tqdm progress (optional; tqdm is try/except imported), handles Content-Disposition
- In extension mode, `FolderPathsModelAdapter` (in `civitai_routes.py`) replaces `ModelManager.find_model()` with ComfyUI's `folder_paths.get_full_path()`

## Supported Scope

### Sidebar Extension
- Sidebar tab registration in ComfyUI UI
- API key management via ComfyUI Settings
- Image metadata query (by ID or full Civitai URL)
- Generation parameter display (prompt, sampler, steps, CFG, seed, size, clip skip, image preview)
- Model status checking (checkpoint, LoRA, VAE, embedding, upscaler) with local existence detection via `folder_paths`
- Model downloading with real-time progress bars, SHA256 verification, cancel/retry support, and batch download
- Workflow generation from fetched metadata, loaded onto canvas with auto-arranged node layout
- ModelCard supports 7 visual states: already downloaded, missing (resolved), missing (unresolved), downloading, verifying, failed, cancelled

### CLI Pipeline
- **txt2img** workflows with optional LoRA(s)
- **txt2img-hires** workflows (two-pass generation with upscaler model)
- CLIP skip support via CLIPSetLastLayer
- Resource resolution via hash, name search, or model version ID (civitaiResources)
- Custom VAE support via VAELoader node (falls back to checkpoint's built-in VAE)
- Embedding (Textual Inversion) support: auto-converts prompt references to `embedding:name` syntax
- Standard ComfyUI nodes: CheckpointLoaderSimple, KSampler, CLIPTextEncode, CLIPSetLastLayer, EmptyLatentImage, VAEDecode, VAEEncode, VAELoader, SaveImage, LoraLoader, UpscaleModelLoader, ImageUpscaleWithModel, ImageScale, LatentUpscale

## Not Yet Supported

- img2img / inpainting
- ControlNet
- Non-standard ComfyUI nodes

## Tested Images

Images verified to work through the full pipeline (fetch → resolve → generate workflow):

| Image ID | URL | Workflow Type | Features |
|----------|-----|---------------|----------|
| 116872916 | https://civitai.com/images/116872916 | txt2img | Basic txt2img with LoRAs, hash-based resource resolution |
| 118577644 | https://civitai.com/images/118577644 | txt2img-hires | Hires fix, 7 LoRAs, upscaler model, clip_skip=2, civitaiResources (version ID resolution), no seed |
| 119258762 | https://civitai.com/images/119258762 | txt2img-hires | Hires fix, 4 LoRAs, custom VAE, 3 embeddings (lazyneg/lazypos/lazyhand), upscaler model, clip_skip=2, no seed |

## Code Style Guidelines

- **Conversation Language**: Use **Traditional Chinese (繁體中文)** when communicating with the user in Claude Code
- **Code Language**: All code, comments, docstrings, commit messages, and documentation files (including README, CLAUDE.md) must be in **English**
- **Docstrings**: Google-style with type hints
- **Dependencies**: `tqdm` and `python-dotenv` are optional (try/except imported); only `requests` is a hard dependency
- **pyproject.toml**: `[project.dependencies]` has only `requests>=2.31.0`. `tqdm` and `python-dotenv` are in `[project.optional-dependencies].cli` for CLI users. `[tool.comfy]` section configured for ComfyUI Registry.
- **Frontend CSS**: Use ComfyUI native CSS variables (`--fg-color`, `--descrip-text`, `--border-color`, `--comfy-input-bg`), NOT PrimeVue tokens (`--p-text-color`, etc.) which don't switch with ComfyUI's dark/light theme

## Environment Setup

### WSL2 / Linux

```bash
# Initial setup
bash scripts/setup.sh

# Check environment
bash scripts/check_env.sh

# Start ComfyUI
bash scripts/run_comfyui.sh
```

### Windows (Native)

```powershell
# 1. Create virtual environment and install core dependencies
uv venv .venv --python 3.12
uv pip install -e ".[cli]"

# 2. Install PyTorch with CUDA 13.0
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# 3. Clone ComfyUI (into sibling directory)
cd ..
git clone https://github.com/comfyanonymous/ComfyUI.git
cd comfyui-civitai-alchemist

# 4. Install ComfyUI dependencies
uv pip install -r ../ComfyUI/requirements.txt

# 5. Build the frontend
cd ui
npm install
npm run build
cd ..

# 6. Set up .env (for CLI mode)
copy .env.example .env
# Edit .env with your Civitai API key and models directory path

# 7. Create directory junctions (Windows equivalent of symlinks)
# Share .venv with ComfyUI:
powershell -Command "New-Item -ItemType Junction -Path ..\ComfyUI\.venv -Target (Resolve-Path .venv)"
# Register as custom node:
powershell -Command "New-Item -ItemType Junction -Path ..\ComfyUI\custom_nodes\comfyui-civitai-alchemist -Target (Resolve-Path .)"

# 8. Start ComfyUI
.venv\Scripts\python -s ..\ComfyUI\main.py
```

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python` for all pipeline commands.

## Known Issues

1. **Flash Attention**: May crash on RTX 5090 — SageAttention is used instead
2. **WSL2**: Project must be in WSL2 filesystem (`/home/...`), not `/mnt/c/`
3. **Python 3.13**: Not supported; use 3.12
4. **Windows**: `triton` and `sageattention` are Linux-only; not available on native Windows. ComfyUI runs fine without them but without SageAttention acceleration
5. **Windows junctions**: Use `New-Item -ItemType Junction` (PowerShell) instead of `ln -s` for directory links. Junctions do not require admin privileges

## References

- [Civitai API Documentation](https://github.com/civitai/civitai/wiki/REST-API-Reference)
- [ComfyUI Custom Nodes Guide](https://docs.comfy.org/development/core-concepts/custom-nodes)
- [ComfyUI Sidebar Tabs API](https://docs.comfy.org/custom-nodes/js/javascript_sidebar_tabs)
- [ComfyUI Extension Settings API](https://docs.comfy.org/custom-nodes/js/javascript_settings)
- [ComfyUI Registry pyproject.toml Spec](https://docs.comfy.org/registry/specifications)
