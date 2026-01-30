"""
Civitai Browser Node
瀏覽 Civitai 上的圖片
"""

class CivitaiBrowserNode:
    """
    瀏覽 Civitai 平台的圖片
    """

    @classmethod
    def INPUT_TYPES(cls):
        """定義輸入參數"""
        return {
            "required": {
                "search_query": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "搜尋關鍵字 (例如: anime, landscape)"
                }),
                "limit": ("INT", {
                    "default": 10,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "display": "number"
                }),
            },
            "optional": {
                "nsfw_filter": ("BOOLEAN", {
                    "default": True,
                    "label_on": "過濾 NSFW",
                    "label_off": "顯示全部"
                }),
                "sort_by": (["Most Reactions", "Most Comments", "Newest"], {
                    "default": "Most Reactions"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("image_urls", "metadata")
    FUNCTION = "browse"
    CATEGORY = "Civitai"
    OUTPUT_NODE = False

    def browse(self, search_query, limit, nsfw_filter=True, sort_by="Most Reactions"):
        """
        瀏覽 Civitai 圖片

        Args:
            search_query: 搜尋關鍵字
            limit: 結果數量
            nsfw_filter: 是否過濾 NSFW 內容
            sort_by: 排序方式

        Returns:
            tuple: (圖片 URLs, metadata JSON)
        """
        # TODO: 實作 Civitai API 呼叫
        # 這裡會使用 utils/civitai_api.py

        print(f"[Civitai Browser] 搜尋: {search_query}, 限制: {limit}, NSFW過濾: {nsfw_filter}, 排序: {sort_by}")

        # 暫時返回範例資料
        image_urls = "https://example.com/image1.jpg,https://example.com/image2.jpg"
        metadata = '{"images": [], "total": 0}'

        return (image_urls, metadata)
