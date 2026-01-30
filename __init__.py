"""
ComfyUI Civitai Alchemist
瀏覽 Civitai 相片、擷取關鍵字、自動下載模組、套用 prompt
"""

from .nodes.civitai_browser import CivitaiBrowserNode
from .nodes.keyword_extractor import KeywordExtractorNode
from .nodes.model_downloader import ModelDownloaderNode
from .nodes.prompt_applier import PromptApplierNode

NODE_CLASS_MAPPINGS = {
    "CivitaiBrowser": CivitaiBrowserNode,
    "KeywordExtractor": KeywordExtractorNode,
    "ModelDownloader": ModelDownloaderNode,
    "PromptApplier": PromptApplierNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CivitaiBrowser": "Civitai Browser 📷",
    "KeywordExtractor": "Keyword Extractor 🔍",
    "ModelDownloader": "Model Downloader ⬇️",
    "PromptApplier": "Prompt Applier ✨",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
