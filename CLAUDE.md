# CLAUDE.md - Development Context

**ComfyUI Civitai Alchemist** reproduces Civitai images locally via ComfyUI, as a ComfyUI sidebar extension or standalone CLI pipeline. See [README.md](README.md) for full usage, installation, and project structure.

## Quick Commands

```bash
# CLI pipeline (Windows: use .venv\Scripts\python)
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX --debug
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX --submit
.venv/bin/python -m pipeline.reproduce https://civitai.com/images/XXXXX --skip-download

# Frontend build
cd ui && npm install && npm run build   # Build to ../js/
cd ui && npm run dev                     # Watch mode

# Start ComfyUI
.venv/Scripts/python -s ../ComfyUI/main.py    # Windows
.venv/bin/python -s ../ComfyUI/main.py        # Linux/WSL2
```

Output goes to `output/`: `metadata.json`, `resources.json`, `workflow.json`, `debug_report.json` (debug only).

## Code Style

- **Conversation**: Traditional Chinese (繁體中文) with the user
- **Code/comments/commits/docs**: English
- **Docstrings**: Google-style with type hints
- **Dependencies**: `requests` is the only hard dep. `tqdm` and `python-dotenv` are optional (try/except imported), listed in `[project.optional-dependencies].cli`
- **Frontend CSS**: Use ComfyUI native CSS variables (`--fg-color`, `--descrip-text`, `--border-color`, `--comfy-input-bg`), NOT PrimeVue tokens (`--p-text-color`, etc.) — PrimeVue tokens don't switch with ComfyUI's dark/light theme

## Architecture Gotchas

### Package naming
`civitai_utils/` was renamed from `utils/` to avoid collision with ComfyUI's own `utils` in `sys.modules`. Do not create a `utils/` package.

### Metadata structure
Civitai API returns nested `meta.meta` — the outer `meta` has an `id`, the inner `meta` has actual generation params. `fetch_metadata.py` unwraps this.

### HTTP client
- Both extension mode and CLI mode use `requests` (synchronous) as the sole HTTP client
- **Extension mode** (`civitai_routes.py`): downloads run in a thread via `asyncio.to_thread()` to avoid blocking ComfyUI's event loop. An `asyncio.Event` → `threading.Event` bridge handles cancellation
- `from aiohttp import web` is still imported for ComfyUI's web framework (route registration, JSON responses) but NOT used as an HTTP client

### Model existence checking
- **Extension mode**: `FolderPathsModelAdapter` uses ComfyUI's `folder_paths.get_full_path()` (respects `extra_model_paths.yaml`)
- **CLI mode**: `ModelManager.find_model()` uses `rglob` on the models directory

### Workflow generation
- Node references use `["node_id", output_index]` format (ComfyUI API-format DAG)
- LoRA nodes are chained: each takes model/clip from the previous node
- Custom VAE: if VAE resource exists, adds VAELoader node; otherwise uses checkpoint's built-in VAE (output index 2)

### Windows-specific
`.part` temp file cleanup in `civitai_routes.py` happens after the file handle is closed (outside `with open()` block) to avoid Windows file locking issues.

### ComfyUI extension registration
- Routes auto-register at import time via `@server.PromptServer.instance.routes.post()` decorators
- `__init__.py` imports `civitai_routes` to trigger this registration
- WebSocket events use `PromptServer.instance.send_sync("civitai.download.progress", ...)` for real-time download progress

## Known Issues

1. **Python 3.13**: Not supported; use 3.12
2. **Windows junctions**: Use `New-Item -ItemType Junction` (PowerShell) instead of `ln -s`. Junctions do not require admin privileges

## Tested Images

| Image ID | URL | Type | Features |
|----------|-----|------|----------|
| 116872916 | https://civitai.com/images/116872916 | txt2img | LoRAs, hash-based resolution |
| 118577644 | https://civitai.com/images/118577644 | txt2img-hires | Hires fix, 7 LoRAs, upscaler, clip_skip=2, civitaiResources, no seed |
| 119258762 | https://civitai.com/images/119258762 | txt2img-hires | Hires fix, 4 LoRAs, custom VAE, 3 embeddings, upscaler, clip_skip=2, no seed |

## References

See [README.md](README.md) for API documentation links and ComfyUI development references.
