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
