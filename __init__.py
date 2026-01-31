"""
ComfyUI Civitai Alchemist

A tool for reproducing Civitai images locally via ComfyUI.
Fetches image metadata, resolves and downloads models,
and generates ComfyUI workflows.

Usage:
    python -m pipeline.reproduce https://civitai.com/images/XXXXX
"""

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

# Register custom API routes when loaded by ComfyUI.
# Importing the module triggers route registration via decorators.
# civitai_routes.py handles its own sys.path setup internally.
try:
    from . import civitai_routes  # noqa: F401
except Exception as e:
    print(f"[Civitai Alchemist] Warning: Failed to register API routes: {e}")
