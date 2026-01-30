"""
Keyword Extractor Node
從 Civitai 圖片 metadata 中擷取關鍵字和設定
"""

class KeywordExtractorNode:
    """
    擷取圖片的 prompt、negative prompt 和生成參數
    """

    @classmethod
    def INPUT_TYPES(cls):
        """定義輸入參數"""
        return {
            "required": {
                "metadata": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "從 Civitai Browser 輸入的 metadata"
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "parameters")
    FUNCTION = "extract"
    CATEGORY = "Civitai"

    def extract(self, metadata):
        """
        擷取關鍵字和參數

        Args:
            metadata: 圖片 metadata JSON

        Returns:
            tuple: (positive prompt, negative prompt, parameters)
        """
        # TODO: 實作 metadata 解析

        print(f"[Keyword Extractor] 解析 metadata...")

        # 暫時返回範例資料
        positive_prompt = "sample positive prompt"
        negative_prompt = "sample negative prompt"
        parameters = "steps: 20, sampler: DPM++ 2M Karras"

        return (positive_prompt, negative_prompt, parameters)
