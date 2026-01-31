# ComfyUI Civitai Alchemist

Paste a Civitai image URL, automatically fetch generation parameters, download required models, and generate a ComfyUI workflow to reproduce the image.

Works as both a **ComfyUI sidebar extension** and a **standalone CLI tool**.

## Features

### ComfyUI Sidebar Extension

- **Sidebar Tab** — Dedicated tab in ComfyUI's left sidebar for quick access
- **API Key Management** — Configure your Civitai API key via ComfyUI's built-in Settings panel
- **Image Lookup** — Enter an image ID or full Civitai URL to fetch generation metadata
- **Generation Info** — View prompt, sampler, steps, CFG, seed, size, clip skip, and image preview
- **Model Status** — See which models (checkpoint, LoRAs, VAE, embeddings, upscaler) are already downloaded and which are missing
- **Model Download** — Download missing models directly from the sidebar with real-time progress bars, SHA256 verification, cancel support, and batch download
- **Workflow Generation** — One-click workflow generation from fetched metadata, automatically loaded onto the ComfyUI canvas with proper node layout

### CLI Pipeline

1. **Fetch Metadata** — Extract prompt, model, LoRA, sampler, and other generation parameters from a Civitai image page
2. **Resolve Models** — Look up model download URLs via hash/name
3. **Download Models** — Automatically download checkpoint, LoRA, VAE, embeddings, and upscaler models to the appropriate ComfyUI directories
4. **Generate Workflow** — Produce a ComfyUI API-format workflow JSON, ready to submit

## Supported Workflows

- **txt2img** — Standard single-pass generation with optional LoRA(s)
- **txt2img-hires** — Two-pass generation with upscaler model (hires fix)
- CLIP skip, custom VAE, embeddings (textual inversion), multi-LoRA chains

## Requirements

- Python 3.10–3.12
- A working [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installation
- A [Civitai API key](https://civitai.com/user/account) (free)
- [Node.js](https://nodejs.org/) 18+ (only needed for frontend development)

## Installation

### Via ComfyUI Manager (Recommended)

1. Open ComfyUI Manager in the ComfyUI interface
2. Search for **Civitai Alchemist**
3. Click **Install**
4. Restart ComfyUI

### Manual Installation

1. Clone into ComfyUI's `custom_nodes/` directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ThePhilosopherStone/comfyui-civitai-alchemist.git
```

2. Start (or restart) ComfyUI. The Civitai Alchemist tab will appear in the left sidebar.

3. Open ComfyUI Settings and enter your Civitai API key in the **Civitai API Key** field.

> **Note:** The pre-built frontend (`js/main.js`) is included in the repository. No Node.js or build step required for end users.

### As a Standalone CLI Tool

```bash
git clone https://github.com/ThePhilosopherStone/comfyui-civitai-alchemist.git
cd comfyui-civitai-alchemist

# Install with CLI extras (tqdm for progress bars, dotenv for .env support)
pip install -e ".[cli]"

# Set up environment variables
cp .env.example .env
# Edit .env — fill in your Civitai API key and models directory path
```

## Usage

### ComfyUI Sidebar

1. Click the Civitai Alchemist icon in the left sidebar
2. Enter a Civitai image ID (e.g. `116872916`) or full URL (e.g. `https://civitai.com/images/116872916`)
3. Click **Go** (or press Enter) to fetch generation info
4. View generation parameters and model availability
5. Click **Download All Missing** to download any missing models (or download individually per model card)
6. Click **Generate Workflow** to create a ComfyUI workflow and load it onto the canvas
7. Press **Queue Prompt** to start generating

### CLI: One-shot (recommended)

```bash
# Full pipeline: fetch → resolve → download → generate workflow
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/116872916

# Generate workflow and submit to running ComfyUI
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/116872916 --submit

# Skip download (models already exist)
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/116872916 --skip-download
```

### CLI: Step by step (for debugging)

Each step produces a JSON file you can inspect:

```bash
# Step 1: Fetch image metadata
.venv/bin/python -m pipeline.fetch_metadata https://civitai.com/images/116872916
# → output/metadata.json

# Step 2: Resolve model download URLs
.venv/bin/python -m pipeline.resolve_models
# → output/resources.json

# Step 3: Download models (preview first with --dry-run)
.venv/bin/python -m pipeline.download_models --dry-run
.venv/bin/python -m pipeline.download_models
# → model files saved to ComfyUI/models/

# Step 4: Generate ComfyUI workflow
.venv/bin/python -m pipeline.generate_workflow
# → output/workflow.json

# Step 4b: Generate and submit to ComfyUI
.venv/bin/python -m pipeline.generate_workflow --submit
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--models-dir PATH` | Path to your ComfyUI models directory (or set `MODELS_DIR` in `.env`) |
| `--submit` | Submit the generated workflow to a running ComfyUI instance |
| `--comfyui-url URL` | ComfyUI server URL (default: `http://127.0.0.1:8188`) |
| `--skip-download` | Skip model download step |
| `--output-dir DIR` | Output directory for JSON files (default: `output`) |
| `--api-key KEY` | Civitai API key (or set `CIVITAI_API_KEY` in `.env`) |

## Project Structure

```
comfyui-civitai-alchemist/
├── __init__.py                 # ComfyUI extension entry point
├── civitai_routes.py           # Backend API routes (fetch, resolve, download, generate)
├── civitai_utils/              # Shared utilities
│   ├── civitai_api.py          # Civitai REST API client (with retry/backoff)
│   └── model_manager.py        # Model download & directory management
├── pipeline/                   # CLI pipeline scripts
│   ├── fetch_metadata.py       # Step 1: URL → metadata.json
│   ├── resolve_models.py       # Step 2: metadata → resources.json
│   ├── download_models.py      # Step 3: download model files
│   ├── generate_workflow.py    # Step 4: generate workflow.json
│   ├── sampler_map.py          # Civitai ↔ ComfyUI sampler name mapping
│   └── reproduce.py            # One-shot runner (all steps)
├── ui/                         # Frontend source (Vue 3 + TypeScript)
│   ├── src/
│   │   ├── main.ts             # Extension entry: sidebar & settings registration
│   │   ├── App.vue             # Root component with state management
│   │   ├── components/         # UI components
│   │   │   ├── ApiKeyWarning.vue
│   │   │   ├── ImageInput.vue
│   │   │   ├── GenerationInfo.vue
│   │   │   ├── ModelList.vue
│   │   │   └── ModelCard.vue
│   │   ├── composables/
│   │   │   └── useCivitaiApi.ts  # API client composable
│   │   └── types/              # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts          # Vite library mode → ../js/
├── js/                         # Built frontend output (committed for distribution)
├── output/                     # CLI pipeline output (gitignored)
├── scripts/                    # Environment setup scripts (Linux/WSL2)
├── pyproject.toml              # Python project config
└── LICENSE                     # MIT License
```

## Frontend Development

The frontend is a Vue 3 + TypeScript project built with Vite in library mode. The build output goes to `js/`, which ComfyUI loads automatically.

```bash
cd ui

# Install dependencies
npm install

# Build for production (outputs to ../js/)
npm run build

# Watch mode for development
npm run dev
```

After building, restart ComfyUI (or refresh the browser) to load the updated frontend.

## Development Setup

### Linux / WSL2

If you want to set up a full development environment (including ComfyUI and PyTorch with CUDA), use the setup script:

```bash
bash scripts/setup.sh
```

This will install PyTorch with CUDA support, clone ComfyUI, set up symlinks, and configure the full development environment.

### Windows (Native)

> **Note:** `triton` and `sageattention` are not available on native Windows. ComfyUI will still work but without SageAttention acceleration.

```powershell
# 1. Create virtual environment and install core dependencies
cd comfyui-civitai-alchemist
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

# 5. Set up environment variables (for CLI mode)
copy .env.example .env
# Edit .env — fill in your Civitai API key and models directory path

# 6. Create directory junctions (Windows equivalent of symlinks)
# Share .venv with ComfyUI:
New-Item -ItemType Junction -Path ..\ComfyUI\.venv -Target (Resolve-Path .venv)
# Register as custom node:
New-Item -ItemType Junction -Path ..\ComfyUI\custom_nodes\comfyui-civitai-alchemist -Target (Resolve-Path .)
```

On Windows, run CLI pipeline commands with:

```powershell
.venv\Scripts\python -m pipeline.reproduce https://civitai.com/images/116872916
```

See [CLAUDE.md](CLAUDE.md) for more development details.

## Not Yet Supported

- img2img / inpainting workflows
- ControlNet
- Non-standard ComfyUI nodes

## References

- [Civitai API Documentation](https://github.com/civitai/civitai/wiki/REST-API-Reference)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)

## License

MIT
