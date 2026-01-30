# CLAUDE.md - Development Context

This file provides context for AI assistants (like Claude) working on this project.

## Project Overview

**ComfyUI Civitai Alchemist** is a ComfyUI custom node extension for browsing Civitai images, extracting metadata, downloading models, and applying prompts.

**Current Status**: Development environment setup is complete. Core functionality (Civitai API integration) is marked as TODO for future implementation.

## Environment Information

- **Hardware**: NVIDIA GeForce RTX 5090 (24GB VRAM)
- **CUDA Version**: 13.0
- **Driver Version**: 581.29
- **OS**: Ubuntu on WSL2
- **Python**: 3.12.3
- **Package Manager**: uv 0.9.27

## Performance Optimizations

The project is optimized for RTX 5090 (Blackwell architecture):

1. **PyTorch 2.7+** with CUDA 12.8 (forward compatible with CUDA 13.0)
2. **SageAttention** (primary acceleration, 1.5-2x speedup)
3. **Flash Attention 2** (optional, may have compatibility issues on RTX 5090)
4. **CUDA optimizations**:
   - `CUDA_MODULE_LOADING=lazy`
   - `TORCH_CUDA_ARCH_LIST="12.0"` (Blackwell sm_120)
   - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`

Expected performance improvement: **2-2.5x** overall speedup vs. no optimization.

## Project Structure

```
comfyui-civitai-alchemist/
├── __init__.py                 # Node registration (currently only ExampleNode)
├── nodes/
│   ├── __init__.py
│   └── example_node.py        # Simple example with API connectivity test
├── utils/
│   ├── __init__.py
│   ├── civitai_api.py         # Civitai API template (TODO)
│   └── model_manager.py       # Model management template (TODO)
├── scripts/
│   ├── setup.sh               # One-click environment setup
│   ├── run_comfyui.sh         # Start ComfyUI
│   ├── check_env.sh           # Environment health check
│   ├── benchmark.sh           # Performance testing
│   ├── link.sh / unlink.sh    # Symlink management
├── docs/
│   └── DEVELOPMENT.md         # Development guide
├── .env                       # Environment variables
├── pyproject.toml             # Project dependencies
└── README.md                  # User documentation
```

## Current Implementation Status

### ✅ Completed

1. **Development Environment**
   - Virtual environment with uv
   - PyTorch 2.7+ with CUDA 12.8 support
   - SageAttention installed
   - Flash Attention (optional)
   - Performance optimization environment variables

2. **Development Scripts**
   - All scripts created and executable
   - WSL2 network configuration (--listen 0.0.0.0)
   - GPU passthrough verification

3. **Project Structure**
   - Basic node registration system
   - Example node with simple API test
   - Template classes for future implementation

4. **Documentation**
   - README with quick start guide
   - DEVELOPMENT.md for Python beginners
   - Inline code documentation (all in English)

### 🔄 TODO (Future Implementation)

1. **Civitai API Integration** (`utils/civitai_api.py`)
   - Implement `search_images()` - Search Civitai images
   - Implement `get_image_metadata()` - Get image metadata
   - Implement `download_model()` - Download models from Civitai
   - API Documentation: https://github.com/civitai/civitai/wiki/REST-API-Reference

2. **Model Management** (`utils/model_manager.py`)
   - Implement `download_file()` with progress bar
   - Add model validation and checksums
   - Handle different model types (checkpoint, lora, vae, embedding)

3. **Custom Nodes** (to be created)
   - **Civitai Browser Node**: Browse and search images
   - **Keyword Extractor Node**: Extract prompts and parameters
   - **Model Downloader Node**: Auto-download required models
   - **Prompt Applier Node**: Apply extracted prompts to workflow

4. **Testing**
   - Unit tests for API wrapper
   - Integration tests for nodes
   - End-to-end workflow tests

## Code Style Guidelines

- **Language**: All code, comments, and docstrings in English
- **User Communication**: Chinese for README, script outputs, user messages
- **Docstrings**: Use Google-style docstrings with type hints
- **Naming**: Clear, descriptive names (avoid abbreviations)
- **TODOs**: Mark unimplemented features with `# TODO:` comments

## Quick Start Commands

```bash
# Initial setup (run once)
bash scripts/setup.sh

# Check environment
bash scripts/check_env.sh

# Start ComfyUI
bash scripts/run_comfyui.sh

# Run performance benchmark
bash scripts/benchmark.sh

# Verify symlinks
bash scripts/link.sh
```

Access ComfyUI:
- From Linux: http://127.0.0.1:8188
- From Windows (WSL2): http://localhost:8188

## Development Workflow

1. **Make changes** in `nodes/` or `utils/`
2. **Restart ComfyUI**: Ctrl+C, then `bash scripts/run_comfyui.sh`
3. **Refresh browser** (F5)
4. **Commit changes**: `git add . && git commit -m "description"`

## Known Issues / Limitations

1. **Flash Attention**: May have kernel crash issues on RTX 5090
   - Workaround: Use SageAttention (installed by default)
   - Status: ComfyUI automatically falls back to working backend

2. **WSL2**: Project files must be in WSL2 filesystem (`/home/...`)
   - Do NOT use `/mnt/c/` for development (slower I/O)
   - Models can be stored on Windows and symlinked if needed

3. **Python 3.13**: Limited support for some packages
   - Use Python 3.12 (currently 3.12.3) ✓

## Important Notes for Future Development

### When Implementing Civitai Integration

1. **API Authentication**
   - Civitai API key is optional for most endpoints
   - Required for user-specific data or higher rate limits
   - Store API key securely (environment variable or config file)

2. **Rate Limiting**
   - Implement exponential backoff for API calls
   - Cache results when appropriate
   - Respect Civitai's rate limits

3. **Error Handling**
   - Handle network errors gracefully
   - Provide clear error messages to users
   - Log errors for debugging

4. **Testing API Calls**
   - Use httpbin.org for connectivity tests (already in example_node.py)
   - Test with real Civitai API in development
   - Add integration tests

### Adding New Nodes

1. Create new file in `nodes/` directory
2. Define node class with:
   - `INPUT_TYPES` classmethod
   - `RETURN_TYPES` and `RETURN_NAMES`
   - `FUNCTION` name
   - `CATEGORY` for organization
3. Register in `__init__.py`:
   - Add to `NODE_CLASS_MAPPINGS`
   - Add to `NODE_DISPLAY_NAME_MAPPINGS`
4. Restart ComfyUI to load new node

## References

- [ComfyUI Custom Nodes Guide](https://docs.comfy.org/development/core-concepts/custom-nodes)
- [Civitai API Documentation](https://github.com/civitai/civitai/wiki/REST-API-Reference)
- [PyTorch 2.7 Release Notes](https://pytorch.org/blog/pytorch-2-7/)
- [SageAttention GitHub](https://github.com/thu-ml/SageAttention)
- [ComfyUI RTX 5090 Support](https://github.com/Comfy-Org/ComfyUI/discussions/6643)

## Git History

- **Initial commit**: Development environment setup with performance optimizations
- **Latest commit**: Simplified nodes to template structure, all code in English

## Contact / Support

For questions during development:
1. Check [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed guide
2. Review example node in [nodes/example_node.py](nodes/example_node.py)
3. Run environment check: `bash scripts/check_env.sh`
4. Check ComfyUI console for error messages

---

**Last Updated**: 2026-01-30
**Project Status**: Environment setup complete, ready for Civitai integration development
