"""
Model Manager
管理 ComfyUI 模型的下載和組織
"""

import os
from pathlib import Path
from typing import Optional


class ModelManager:
    """
    模型管理器
    """

    def __init__(self, comfyui_path: Optional[str] = None):
        """
        初始化模型管理器

        Args:
            comfyui_path: ComfyUI 根目錄路徑
        """
        if comfyui_path is None:
            # 預設假設在 ../ComfyUI
            self.comfyui_path = Path(__file__).parent.parent.parent / "ComfyUI"
        else:
            self.comfyui_path = Path(comfyui_path)

        self.models_path = self.comfyui_path / "models"

    def get_model_dir(self, model_type: str) -> Path:
        """
        獲取特定類型模型的目錄

        Args:
            model_type: 模型類型 (checkpoint, lora, vae, embedding)

        Returns:
            模型目錄路徑
        """
        type_mapping = {
            "checkpoint": "checkpoints",
            "lora": "loras",
            "vae": "vae",
            "embedding": "embeddings"
        }

        dir_name = type_mapping.get(model_type, model_type)
        return self.models_path / dir_name

    def download_file(self, url: str, destination: Path) -> Path:
        """
        下載檔案

        Args:
            url: 下載 URL
            destination: 目標路徑

        Returns:
            下載完成的檔案路徑
        """
        # TODO: 實作檔案下載,包含進度顯示
        print(f"下載 {url} 到 {destination}")
        return destination

    def list_models(self, model_type: str) -> list:
        """
        列出特定類型的所有模型

        Args:
            model_type: 模型類型

        Returns:
            模型檔案列表
        """
        model_dir = self.get_model_dir(model_type)
        if not model_dir.exists():
            return []

        # 支援的模型檔案格式
        extensions = [".safetensors", ".ckpt", ".pt", ".pth"]
        models = []

        for ext in extensions:
            models.extend(model_dir.glob(f"*{ext}"))

        return [m.name for m in models]
