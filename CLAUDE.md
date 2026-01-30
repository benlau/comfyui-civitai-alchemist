# CLAUDE.md - Development Context

This file provides context for AI assistants (like Claude) working on this project.

## Project Overview

**ComfyUI Civitai Alchemist** reproduces Civitai images locally via ComfyUI. Given a Civitai image URL, it fetches generation metadata, resolves and downloads required models, and generates a ComfyUI workflow.

## Environment Information

- **Hardware**: NVIDIA GeForce RTX 5090 (24GB VRAM)
- **CUDA Version**: 13.0
- **Driver Version**: 581.29
- **OS**: Ubuntu on WSL2
- **Python**: 3.12.3
- **Package Manager**: uv 0.9.27
- **ComfyUI path**: `../ComfyUI` (relative to project root)

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

Generated images from ComfyUI go to `../ComfyUI/output/`.

## Project Structure

```
comfyui-civitai-alchemist/
├── __init__.py                 # ComfyUI node registration (empty)
├── pipeline/                   # Main pipeline scripts
│   ├── fetch_metadata.py       # Step 1: URL → metadata.json
│   ├── resolve_models.py       # Step 2: metadata → resources.json
│   ├── download_models.py      # Step 3: download model files
│   ├── generate_workflow.py    # Step 4: generate workflow.json
│   ├── sampler_map.py          # Civitai ↔ ComfyUI sampler name mapping
│   └── reproduce.py            # One-shot runner (all steps)
├── utils/
│   ├── civitai_api.py          # Civitai REST API client (with retry/backoff)
│   └── model_manager.py        # Model download & directory management
├── nodes/                      # ComfyUI custom nodes (currently unused)
├── scripts/                    # Environment setup scripts
│   ├── setup.sh                # One-click environment setup
│   ├── run_comfyui.sh          # Start ComfyUI
│   ├── check_env.sh            # Environment health check
│   ├── benchmark.sh            # Performance testing
│   └── link.sh / unlink.sh    # Symlink management
├── .env                        # Environment variables (gitignored)
├── .env.example                # Template for .env
├── pyproject.toml              # Project dependencies
└── README.md                   # User documentation
```

## Key Implementation Details

### Civitai API (`utils/civitai_api.py`)

- `get_image_metadata(image_id)` — `GET /api/v1/images?imageId={id}`, returns first item
- `get_model_version_by_hash(hash)` — `GET /api/v1/model-versions/by-hash/{hash}`
- `search_models(query, limit)` — `GET /api/v1/models?query={query}&limit={limit}`
- Retry logic: 3 retries with exponential backoff (1s, 2s, 4s)
- Rate limit handling: respects 429 Retry-After header
- API key loaded from `CIVITAI_API_KEY` env var (via dotenv)

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
- VAE comes from checkpoint (output index 2)
- SaveImage prefix: `civitai_{image_id}`

### Model Manager (`utils/model_manager.py`)

- `TYPE_MAPPING` maps Civitai type names to ComfyUI subdirectories
- `find_model()` searches recursively with `rglob`
- `download_file()` streams with tqdm progress, handles Content-Disposition

## Supported Scope

- **txt2img** workflows with optional LoRA(s)
- Standard ComfyUI nodes: CheckpointLoaderSimple, KSampler, CLIPTextEncode, EmptyLatentImage, VAEDecode, SaveImage, LoraLoader
- Uses checkpoint's built-in VAE

## Not Yet Supported

- img2img / inpainting
- ControlNet
- Hires fix / upscaling
- Custom VAE override
- Non-standard ComfyUI nodes

## Code Style Guidelines

- **Language**: All code, comments, and docstrings in English
- **Docstrings**: Google-style with type hints
- **Dependencies**: Use dotenv for environment variables; all pipeline scripts call `load_dotenv()` in `main()`

## Environment Setup

```bash
# Initial setup
bash scripts/setup.sh

# Check environment
bash scripts/check_env.sh

# Start ComfyUI
bash scripts/run_comfyui.sh
```

## Known Issues

1. **Flash Attention**: May crash on RTX 5090 — SageAttention is used instead
2. **WSL2**: Project must be in WSL2 filesystem (`/home/...`), not `/mnt/c/`
3. **Python 3.13**: Not supported; use 3.12

## References

- [Civitai API Documentation](https://github.com/civitai/civitai/wiki/REST-API-Reference)
- [ComfyUI Custom Nodes Guide](https://docs.comfy.org/development/core-concepts/custom-nodes)
