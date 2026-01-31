"""
API Routes for Civitai Alchemist ComfyUI Extension

Registers custom API endpoints on the ComfyUI PromptServer for
fetching Civitai image metadata and resolving model resources.

Routes are registered at import time via decorators, following the
standard ComfyUI custom node pattern (same approach as comfyui-deploy).
"""

import sys
from pathlib import Path

# Add extension root to sys.path so submodules (pipeline/, civitai_utils/)
# can be imported. The old `utils/` was renamed to `civitai_utils/` to avoid
# collision with ComfyUI's own `utils` package (which gets cached in
# sys.modules at startup).
_EXT_ROOT = str(Path(__file__).resolve().parent)
if _EXT_ROOT not in sys.path:
    sys.path.append(_EXT_ROOT)

from aiohttp import web
import server

import folder_paths

from pipeline.fetch_metadata import parse_image_id, extract_metadata
from pipeline.resolve_models import resolve_resource
from civitai_utils.civitai_api import CivitaiAPI
from civitai_utils.model_manager import ModelManager


# Civitai type -> folder_paths folder name
FOLDER_PATHS_TYPE_MAPPING = {
    "checkpoint": "checkpoints",
    "lora": "loras",
    "vae": "vae",
    "embedding": "embeddings",
    "upscaler": "upscale_models",
}


class FolderPathsModelAdapter:
    """
    Adapter that mimics the ModelManager interface but uses ComfyUI's
    folder_paths module for model lookups. This ensures model searches
    respect the user's ComfyUI configuration (extra_model_paths.yaml, etc.).
    """

    # Reuse TYPE_MAPPING from ModelManager for compatibility with resolve_resource
    TYPE_MAPPING = ModelManager.TYPE_MAPPING

    def get_model_dir(self, model_type: str):
        """
        Get the primary directory for a model type.

        Returns a Path object. Uses the first path from folder_paths
        for the mapped folder name.
        """
        folder_name = FOLDER_PATHS_TYPE_MAPPING.get(model_type)
        if folder_name:
            try:
                paths = folder_paths.get_folder_paths(folder_name)
                if paths:
                    return Path(paths[0])
            except Exception:
                pass
        return Path(f"models/{ModelManager.TYPE_MAPPING.get(model_type, model_type)}")

    def find_model(self, filename: str, model_type: str):
        """
        Check if a model file exists using folder_paths.

        Args:
            filename: Model filename to search for
            model_type: Model type (checkpoint, lora, vae, etc.)

        Returns:
            Path if found, None otherwise
        """
        folder_name = FOLDER_PATHS_TYPE_MAPPING.get(model_type)
        if not folder_name:
            return None

        full_path = folder_paths.get_full_path(folder_name, filename)
        if full_path:
            return Path(full_path)
        return None


routes = server.PromptServer.instance.routes


@routes.post("/civitai/fetch")
async def handle_fetch_metadata(request):
    """
    POST /civitai/fetch

    Accepts: { "image_id": "116872916" or URL, "api_key": "sk_..." }
    Returns: metadata JSON
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"error": "Invalid JSON in request body"},
            status=400,
        )

    image_id_input = data.get("image_id", "")
    api_key = data.get("api_key", "")

    if not image_id_input:
        return web.json_response(
            {"error": "image_id is required"},
            status=400,
        )

    if not api_key:
        return web.json_response(
            {"error": "API key is required. Configure it in ComfyUI Settings."},
            status=401,
        )

    # Parse image ID from URL or bare number
    try:
        image_id = parse_image_id(str(image_id_input))
    except ValueError as e:
        return web.json_response(
            {"error": f"Invalid image ID format: {e}"},
            status=400,
        )

    # Fetch from Civitai API
    api = CivitaiAPI(api_key=api_key)
    try:
        image_data = api.get_image_metadata(image_id)
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            return web.json_response(
                {"error": "Invalid API key"},
                status=401,
            )
        # Civitai may return 500 for non-existent large IDs
        if "500" in error_msg:
            return web.json_response(
                {"error": "Image not found"},
                status=404,
            )
        return web.json_response(
            {"error": f"Failed to fetch from Civitai API: {error_msg}"},
            status=502,
        )

    if image_data is None:
        return web.json_response(
            {"error": "Image not found"},
            status=404,
        )

    metadata = extract_metadata(image_data)
    return web.json_response(metadata)


@routes.post("/civitai/resolve")
async def handle_resolve_models(request):
    """
    POST /civitai/resolve

    Accepts: { "metadata": {...}, "api_key": "sk_..." }
    Returns: { "resources": [...], "resolved_count": N, "unresolved_count": N }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"error": "Invalid JSON in request body"},
            status=400,
        )

    metadata = data.get("metadata")
    api_key = data.get("api_key", "")

    if not metadata:
        return web.json_response(
            {"error": "metadata is required"},
            status=400,
        )

    if not api_key:
        return web.json_response(
            {"error": "API key is required. Configure it in ComfyUI Settings."},
            status=401,
        )

    resources = metadata.get("resources", [])
    if not resources:
        return web.json_response({
            "resources": [],
            "resolved_count": 0,
            "unresolved_count": 0,
        })

    api = CivitaiAPI(api_key=api_key)
    adapter = FolderPathsModelAdapter()

    resolved = []
    unresolved = []

    for r in resources:
        try:
            result = resolve_resource(r, api, adapter)
            if result.get("resolved"):
                resolved.append(result)
            else:
                unresolved.append(result)
        except Exception as e:
            r_copy = {**r, "resolved": False, "error": str(e)}
            unresolved.append(r_copy)

    all_resources = resolved + unresolved
    return web.json_response({
        "resources": all_resources,
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
    })
