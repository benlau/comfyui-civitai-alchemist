# Development Guide

## For Python Beginners

This guide helps you understand and develop ComfyUI custom nodes, even if you're new to Python.

### Understanding the Structure

This project is a **custom node** for ComfyUI - think of it as a plugin that adds new capabilities.

**Key concepts:**
- **Node**: A processing unit in ComfyUI's visual workflow
- **Virtual Environment**: An isolated Python environment (`.venv/`)
- **Dependencies**: Python packages this project needs
- **Symlink**: A shortcut that makes our code visible to ComfyUI

### Development Workflow

1. **Make changes** in `nodes/` directory
2. **Restart ComfyUI** (Ctrl+C, then `bash scripts/run_comfyui.sh`)
3. **Test** in the browser
4. **Commit** your changes with git

### Adding a New Node

1. Create a new file in `nodes/`, e.g., `my_new_node.py`

2. Define your node class (see `civitai_browser.py` as example):

```python
class MyNewNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "process"
    CATEGORY = "Civitai"

    def process(self, input_text):
        # Your processing logic here
        result = input_text.upper()
        return (result,)
```

3. Register it in `__init__.py`:

```python
from .nodes.my_new_node import MyNewNode

NODE_CLASS_MAPPINGS["MyNewNode"] = MyNewNode
NODE_DISPLAY_NAME_MAPPINGS["MyNewNode"] = "My New Node 🎉"
```

4. Restart ComfyUI to see your node

### Installing Additional Dependencies

If you need a new Python package:

1. Activate virtual environment: `source .venv/bin/activate`
2. Install with uv: `uv pip install package-name`
3. Add to `pyproject.toml` dependencies list
4. Commit the changes

### Debugging

**Print debugging:**
```python
def my_function(self, input_value):
    print(f"Debug: input_value = {input_value}")  # Shows in ComfyUI console
    # ... your code
```

**Check ComfyUI console**: Look for errors when nodes load

**Python debugging:**
```python
import pdb; pdb.set_trace()  # Add breakpoint
```

### Common Issues

**"Module not found"**:
- Check virtual environment is activated
- Install missing package: `uv pip install package-name`

**"Node not appearing in ComfyUI"**:
- Check `__init__.py` has correct mappings
- Look for Python errors in ComfyUI console
- Verify symlink: `ls -la ../ComfyUI/custom_nodes/`

**"CUDA out of memory"**:
- Your GPU ran out of memory
- Try with smaller batch sizes or images

## Advanced Topics

### Using the Civitai API

See `utils/civitai_api.py` for API wrapper.

Example usage:
```python
from utils.civitai_api import CivitaiAPI

api = CivitaiAPI()
images = api.search_images("anime", limit=10)
```

### Model Management

Models are stored in `../ComfyUI/models/`. Use `utils/model_manager.py` to handle downloads.

Example:
```python
from utils.model_manager import ModelManager

manager = ModelManager()
checkpoint_dir = manager.get_model_dir("checkpoint")
models = manager.list_models("checkpoint")
```

### Testing

Run tests:
```bash
source .venv/bin/activate
pytest tests/
```

### Performance Optimization

#### Understanding Attention Backends

ComfyUI automatically selects the best attention implementation:

1. **Flash Attention** (if available) - Fastest, but may have compatibility issues
2. **SageAttention** (if available) - Very fast, reliable for RTX GPUs
3. **PyTorch SDPA** (always available) - Good baseline performance

You don't need to do anything - ComfyUI handles this automatically!

#### Checking Active Backend

When you start ComfyUI, check the console output:
```
Using SageAttention for optimization
```

Or run the benchmark:
```bash
bash scripts/benchmark.sh
```

#### Environment Variables

Performance optimizations are set in `.env`:

```bash
# Lazy loading (faster startup)
export CUDA_MODULE_LOADING=lazy

# Blackwell architecture
export TORCH_CUDA_ARCH_LIST="12.0"

# Memory optimization
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

These are automatically loaded by `run_comfyui.sh`.

### WSL2 Development

#### File System

- Keep project files in WSL2 (`/home/user/...`)
- Avoid `/mnt/c/` for development (slower)
- Models can be on Windows and symlinked

#### Networking

- ComfyUI listens on `0.0.0.0` to allow Windows access
- From Windows: `http://localhost:8188`
- From Linux: `http://127.0.0.1:8188`

#### GPU Access

- Verify with: `nvidia-smi`
- If not working, restart WSL: `wsl --shutdown` (Windows PowerShell)

### Code Style

- Use English for all code, comments, and docstrings
- Follow PEP 8 style guidelines
- Add type hints when possible
- Write clear docstrings

Example:
```python
def process_image(url: str, size: int = 512) -> str:
    """
    Download and process an image from URL.

    Args:
        url: Image URL to download
        size: Target size in pixels

    Returns:
        Path to processed image

    Raises:
        ValueError: If URL is invalid
    """
    # Implementation here
    pass
```

### Git Workflow

```bash
# Check status
git status

# Stage changes
git add nodes/my_new_node.py

# Commit with descriptive message
git commit -m "Add image preprocessing node"

# Push to remote
git push origin main
```

### Useful Resources

- [Python Official Tutorial](https://docs.python.org/3/tutorial/)
- [ComfyUI Development Docs](https://docs.comfy.org/development/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [Civitai API Reference](https://github.com/civitai/civitai/wiki/REST-API-Reference)

## Getting Help

- Check ComfyUI console for error messages
- Run `bash scripts/check_env.sh` to verify environment
- Look at existing nodes for examples
- Search ComfyUI GitHub issues for similar problems

## Best Practices

1. **Test frequently** - Restart ComfyUI after changes
2. **Start simple** - Get basic functionality working first
3. **Use print debugging** - Output to console is easy to see
4. **Read existing code** - Learn from other nodes
5. **Commit often** - Save your progress regularly

Happy developing! 🚀
