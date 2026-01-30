"""
Prompt Applier Node
套用擷取的 prompt 到工作流程
"""

class PromptApplierNode:
    """
    將擷取的 prompt 套用到生成流程
    """

    @classmethod
    def INPUT_TYPES(cls):
        """定義輸入參數"""
        return {
            "required": {
                "positive_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "從 Keyword Extractor 輸入"
                }),
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "從 Keyword Extractor 輸入"
                }),
            },
            "optional": {
                "prepend_text": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "在 prompt 前面加入的文字"
                }),
                "append_text": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "在 prompt 後面加入的文字"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("final_positive", "final_negative")
    FUNCTION = "apply"
    CATEGORY = "Civitai"

    def apply(self, positive_prompt, negative_prompt, prepend_text="", append_text=""):
        """
        套用 prompt

        Args:
            positive_prompt: positive prompt
            negative_prompt: negative prompt
            prepend_text: 前綴文字
            append_text: 後綴文字

        Returns:
            tuple: (最終 positive prompt, 最終 negative prompt)
        """
        # 組合 prompt
        final_positive = f"{prepend_text} {positive_prompt} {append_text}".strip()
        final_negative = negative_prompt

        print(f"[Prompt Applier] 套用 prompt")
        print(f"  Positive: {final_positive[:100]}...")
        print(f"  Negative: {final_negative[:100]}...")

        return (final_positive, final_negative)
