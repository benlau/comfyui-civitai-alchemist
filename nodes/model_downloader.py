"""
Model Downloader Node
自動下載 Civitai 模型
"""

class ModelDownloaderNode:
    """
    下載 Civitai 模型到 ComfyUI models 目錄
    """

    @classmethod
    def INPUT_TYPES(cls):
        """定義輸入參數"""
        return {
            "required": {
                "model_url": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Civitai 模型 URL"
                }),
                "model_type": (["checkpoint", "lora", "vae", "embedding"], {
                    "default": "checkpoint"
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("model_path",)
    FUNCTION = "download"
    CATEGORY = "Civitai"
    OUTPUT_NODE = True

    def download(self, model_url, model_type):
        """
        下載模型

        Args:
            model_url: 模型下載 URL
            model_type: 模型類型

        Returns:
            str: 下載後的模型路徑
        """
        # TODO: 實作模型下載邏輯
        # 使用 utils/model_manager.py

        print(f"[Model Downloader] 下載模型: {model_url} (類型: {model_type})")

        # 暫時返回範例路徑
        model_path = f"/path/to/models/{model_type}/example_model.safetensors"

        return (model_path,)
