"""
Model Manager

Manages ComfyUI model downloads and directory organization.
"""

import os
import re
from pathlib import Path
from typing import List, Optional

import requests

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


class ModelManager:
    """
    Model manager for organizing and downloading ComfyUI models.
    """

    # Map various type names to ComfyUI model subdirectory names
    TYPE_MAPPING = {
        "checkpoint": "checkpoints",
        "Checkpoint": "checkpoints",
        "model": "checkpoints",
        "lora": "loras",
        "LORA": "loras",
        "LoCon": "loras",
        "vae": "vae",
        "VAE": "vae",
        "embedding": "embeddings",
        "TextualInversion": "embeddings",
        "controlnet": "controlnet",
        "hypernetwork": "hypernetworks",
        "upscaler": "upscale_models",
        "Upscaler": "upscale_models",
    }

    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialize model manager.

        Args:
            models_dir: Path to ComfyUI models directory (e.g. /path/to/ComfyUI/models).
                        Falls back to MODELS_DIR env var, then ../ComfyUI/models.
        """
        if models_dir is None:
            models_dir = os.environ.get("MODELS_DIR")

        if models_dir:
            self.models_path = Path(models_dir)
        else:
            self.models_path = Path(__file__).parent.parent.parent / "ComfyUI" / "models"

    def get_model_dir(self, model_type: str) -> Path:
        """
        Get directory for specific model type.

        Args:
            model_type: Model type (checkpoint, lora, vae, embedding, etc.)

        Returns:
            Path to model directory
        """
        dir_name = self.TYPE_MAPPING.get(model_type, model_type)
        return self.models_path / dir_name

    def find_model(self, filename: str, model_type: str) -> Optional[Path]:
        """
        Check if a model file already exists in the ComfyUI directory.

        Searches recursively in the appropriate model subdirectory.

        Args:
            filename: Model filename to search for
            model_type: Model type

        Returns:
            Path to existing file, or None if not found
        """
        model_dir = self.get_model_dir(model_type)
        if not model_dir.exists():
            return None

        for f in model_dir.rglob(filename):
            return f
        return None

    def download_file(
        self,
        url: str,
        destination: Path,
        api_key: Optional[str] = None,
    ) -> Path:
        """
        Download a file with progress bar.

        Handles redirects and Content-Disposition headers for filename detection.

        Args:
            url: Download URL
            destination: Target file path
            api_key: Optional API key for authenticated downloads

        Returns:
            Path to the downloaded file
        """
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        response = requests.get(url, headers=headers, stream=True, timeout=30,
                                allow_redirects=True)
        response.raise_for_status()

        # Check Content-Disposition for actual filename
        content_disp = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disp:
            match = re.search(r'filename="?([^";\n]+)"?', content_disp)
            if match:
                actual_filename = match.group(1).strip()
                destination = destination.parent / actual_filename

        # Ensure target directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        total_size = int(response.headers.get("Content-Length", 0))

        with open(destination, "wb") as f:
            if tqdm:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=destination.name,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return destination

    def list_models(self, model_type: str) -> List[str]:
        """
        List all models of specific type.

        Args:
            model_type: Model type

        Returns:
            List of model filenames
        """
        model_dir = self.get_model_dir(model_type)
        if not model_dir.exists():
            return []

        extensions = [".safetensors", ".ckpt", ".pt", ".pth"]
        models = []
        for ext in extensions:
            models.extend(model_dir.rglob(f"*{ext}"))

        return [m.name for m in models]
