# ComfyUI Civitai Alchemist

ComfyUI custom node for browsing Civitai images, extracting metadata, auto-downloading models, and applying prompts.

## Features

- 📷 **Civitai Browser**: Browse and search Civitai images
- 🔍 **Keyword Extractor**: Extract keywords and settings from images
- ⬇️ **Model Downloader**: Automatically download required models
- ✨ **Prompt Applier**: Apply extracted prompts to your workflow

## Performance Optimization

This project is optimized for **RTX 5090 (Blackwell architecture)** with:
- **SageAttention**: 1.5-2x speed boost (primary acceleration)
- **Flash Attention 2**: Optional, additional acceleration if compatible
- **PyTorch 2.7+**: Blackwell architecture optimizations
- **CUDA 12.8/13.0**: Full GPU compute capability support

## Requirements

- Python 3.10-3.12 (tested with 3.12)
- NVIDIA GPU with CUDA 12.8+ (optimized for RTX 5090)
- uv package manager
- Git
- Ubuntu on WSL2 (or native Linux)

## Quick Start

### 1. Initial Setup

Run the setup script to install everything:

```bash
bash scripts/setup.sh
```

This will:
- Create a virtual environment
- Install PyTorch 2.7+ with CUDA 12.8 support
- Install SageAttention for acceleration
- Optionally install Flash Attention
- Download ComfyUI
- Link this custom node to ComfyUI
- Configure performance optimizations

### 2. Start ComfyUI

```bash
bash scripts/run_comfyui.sh
```

Open in your browser:
- From Linux: `http://127.0.0.1:8188`
- From Windows (WSL2): `http://localhost:8188`

### 3. Find Your Nodes

In ComfyUI:
1. Right-click → Add Node → Civitai
2. You'll see 4 nodes:
   - Civitai Browser 📷
   - Keyword Extractor 🔍
   - Model Downloader ⬇️
   - Prompt Applier ✨

## Development

### Project Structure

```
comfyui-civitai-alchemist/
├── nodes/              # Node implementations
├── utils/              # Helper utilities
├── scripts/            # Development scripts
├── docs/               # Documentation
└── __init__.py         # Node registration
```

### Making Changes

1. Edit files in `nodes/` or `utils/`
2. Restart ComfyUI: Ctrl+C and run `bash scripts/run_comfyui.sh` again
3. Refresh browser (F5)

### Useful Commands

```bash
# Check environment health
bash scripts/check_env.sh

# Run performance benchmark
bash scripts/benchmark.sh

# Re-link to ComfyUI
bash scripts/link.sh

# Unlink from ComfyUI
bash scripts/unlink.sh
```

## Performance Verification

After setup, verify your performance optimizations:

```bash
# 1. Check environment
bash scripts/check_env.sh

# 2. Run benchmark
bash scripts/benchmark.sh

# 3. Check ComfyUI console output
bash scripts/run_comfyui.sh
# Look for "Using SageAttention" or "Using Flash Attention"
```

Expected performance improvements (vs. no optimization):
- **SageAttention**: 1.5-2.0x inference speed
- **torch.compile**: 1.2-1.3x additional boost
- **Overall**: 2-2.5x total speedup

## Troubleshooting

### CUDA not available

WSL2-specific checks:
1. Check GPU passthrough: `nvidia-smi` (should show RTX 5090)
2. Check PyTorch: `python -c "import torch; print(torch.cuda.is_available())"`
3. If CUDA is unavailable, restart WSL: `wsl --shutdown` (in Windows PowerShell)

### SageAttention not working

```bash
source .venv/bin/activate
pip list | grep sageattention
# If not found:
uv pip install sageattention
```

### Custom nodes not appearing

1. Check symlink: `ls -la ../ComfyUI/custom_nodes/`
2. Check ComfyUI console for errors
3. Verify `__init__.py` has correct NODE_CLASS_MAPPINGS
4. Re-run setup: `bash scripts/setup.sh`

### Performance not as expected

1. Run benchmark: `bash scripts/benchmark.sh`
2. Check GPU usage: `nvidia-smi -l 1` (should be near 100%)
3. Verify attention backend in ComfyUI console
4. Check environment variables: `source .env && echo $CUDA_MODULE_LOADING`

## WSL2 Notes

- Project files should be in WSL2 filesystem (`/home/...`), NOT `/mnt/c/`
- Access ComfyUI from Windows: `http://localhost:8188`
- Models can be stored in Windows and symlinked if needed
- GPU passthrough requires Windows 11 or Windows 10 21H2+

## Documentation

- [Development Guide](docs/DEVELOPMENT.md) - Detailed development guide for Python beginners
- [Civitai API Documentation](https://github.com/civitai/civitai/wiki/REST-API-Reference)
- [ComfyUI Custom Nodes Guide](https://docs.comfy.org/development/core-concepts/custom-nodes)

## Performance Resources

- [PyTorch 2.7 Release Notes](https://pytorch.org/blog/pytorch-2-7/)
- [SageAttention GitHub](https://github.com/thu-ml/SageAttention)
- [Flash Attention GitHub](https://github.com/Dao-AILab/flash-attention)
- [ComfyUI RTX 5090 Support](https://github.com/Comfy-Org/ComfyUI/discussions/6643)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
