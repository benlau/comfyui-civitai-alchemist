"""
API Routes for Civitai Alchemist ComfyUI Extension

Registers custom API endpoints on the ComfyUI PromptServer for
fetching Civitai image metadata, resolving model resources,
downloading models, and generating workflows.

Routes are registered at import time via decorators, following the
standard ComfyUI custom node pattern (same approach as comfyui-deploy).
"""

import asyncio
import hashlib
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

# Add extension root to sys.path so submodules (pipeline/, civitai_utils/)
# can be imported. The old `utils/` was renamed to `civitai_utils/` to avoid
# collision with ComfyUI's own `utils` package (which gets cached in
# sys.modules at startup).
_EXT_ROOT = str(Path(__file__).resolve().parent)
if _EXT_ROOT not in sys.path:
    sys.path.append(_EXT_ROOT)

import aiohttp
from aiohttp import web
import server

import folder_paths

from pipeline.fetch_metadata import parse_image_id, extract_metadata
from pipeline.resolve_models import resolve_resource
from pipeline.generate_workflow import build_workflow
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


# ── Download infrastructure ──────────────────────────────────────────


DOWNLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB
PROGRESS_INTERVAL = 0.5  # seconds between WebSocket progress updates


@dataclass
class DownloadTask:
    """Tracks state for an in-flight download task."""
    task_id: str
    asyncio_task: Optional[asyncio.Task] = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    resources: list = field(default_factory=list)


# Module-level registry of active downloads
_active_downloads: Dict[str, DownloadTask] = {}


def _send_progress(task_id: str, filename: str, status: str,
                   progress: int = 0, downloaded_bytes: int = 0,
                   total_bytes: int = 0, error: str = ""):
    """Push a download progress event via WebSocket."""
    server.PromptServer.instance.send_sync("civitai.download.progress", {
        "task_id": task_id,
        "filename": filename,
        "status": status,
        "progress": progress,
        "downloaded_bytes": downloaded_bytes,
        "total_bytes": total_bytes,
        "error": error,
    })


async def _download_single(resource: dict, api_key: str, task_id: str,
                           cancel_event: asyncio.Event) -> bool:
    """
    Download a single model file asynchronously.

    Writes to a .part temp file, verifies SHA256, then renames.
    Returns True on success, False on failure/cancel.
    """
    adapter = FolderPathsModelAdapter()
    model_type = resource.get("type", "checkpoint")
    filename = resource.get("filename", "model.safetensors")
    download_url = resource.get("download_url", "")

    if not download_url:
        _send_progress(task_id, filename, "failed", error="No download URL")
        return False

    # Determine target directory
    target_dir = adapter.get_model_dir(model_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    part_path = target_dir / f"{filename}.part"

    # Civitai download URL needs API key as query parameter
    separator = "&" if "?" in download_url else "?"
    auth_url = f"{download_url}{separator}token={api_key}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(auth_url, timeout=aiohttp.ClientTimeout(total=None, connect=60)) as resp:
                if resp.status != 200:
                    error_msg = f"HTTP {resp.status}"
                    _send_progress(task_id, filename, "failed", error=error_msg)
                    return False

                # Check Content-Disposition for actual filename
                content_disp = resp.headers.get("Content-Disposition", "")
                if "filename=" in content_disp:
                    match = re.search(r'filename="?([^";\n]+)"?', content_disp)
                    if match:
                        actual_filename = match.group(1).strip()
                        filename = actual_filename
                        target_path = target_dir / filename
                        part_path = target_dir / f"{filename}.part"

                total_bytes = int(resp.headers.get("Content-Length", 0))
                downloaded_bytes = 0
                last_progress_time = 0.0
                sha256_hash = hashlib.sha256()

                cancelled = False
                with open(part_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                        if cancel_event.is_set():
                            cancelled = True
                            break

                        f.write(chunk)
                        sha256_hash.update(chunk)
                        downloaded_bytes += len(chunk)

                        # Throttle progress updates (inside with block)
                        now = time.monotonic()
                        if now - last_progress_time >= PROGRESS_INTERVAL:
                            last_progress_time = now
                            progress = int(downloaded_bytes * 100 / total_bytes) if total_bytes else 0
                            _send_progress(task_id, filename, "downloading",
                                           progress=progress,
                                           downloaded_bytes=downloaded_bytes,
                                           total_bytes=total_bytes)

                # File handle is now closed; safe to delete on Windows
                if cancelled:
                    _cleanup_part(part_path)
                    _send_progress(task_id, filename, "cancelled")
                    return False

                # Final 100% progress
                _send_progress(task_id, filename, "downloading",
                               progress=100,
                               downloaded_bytes=downloaded_bytes,
                               total_bytes=total_bytes)

        # SHA256 verification
        _send_progress(task_id, filename, "verifying",
                       downloaded_bytes=downloaded_bytes,
                       total_bytes=total_bytes)

        expected_hash = _get_expected_hash(resource)
        if expected_hash:
            actual_hash = sha256_hash.hexdigest().upper()
            if actual_hash != expected_hash.upper():
                _cleanup_part(part_path)
                _send_progress(task_id, filename, "failed",
                               error="Checksum mismatch")
                return False

        # Rename .part to final filename
        if target_path.exists():
            target_path.unlink()
        part_path.rename(target_path)

        _send_progress(task_id, filename, "completed",
                       progress=100,
                       downloaded_bytes=downloaded_bytes,
                       total_bytes=total_bytes)
        return True

    except asyncio.CancelledError:
        _cleanup_part(part_path)
        _send_progress(task_id, filename, "cancelled")
        return False
    except Exception as e:
        _cleanup_part(part_path)
        _send_progress(task_id, filename, "failed", error=str(e))
        return False


def _get_expected_hash(resource: dict) -> Optional[str]:
    """Extract expected SHA256 hash from resource dict."""
    hashes = resource.get("hashes")
    if isinstance(hashes, dict):
        return hashes.get("SHA256")
    return None


def _cleanup_part(part_path: Path):
    """Delete .part file if it exists."""
    try:
        if part_path.exists():
            part_path.unlink()
    except OSError:
        pass


async def _run_single_download(resource: dict, api_key: str, task_id: str,
                               cancel_event: asyncio.Event):
    """Coroutine wrapper for single download task."""
    try:
        await _download_single(resource, api_key, task_id, cancel_event)
    finally:
        _active_downloads.pop(task_id, None)


async def _run_batch_download(resources: list, api_key: str, task_id: str,
                              cancel_event: asyncio.Event):
    """Coroutine wrapper for batch download: downloads resources sequentially."""
    try:
        for resource in resources:
            if cancel_event.is_set():
                # Send cancelled for remaining resources
                filename = resource.get("filename", "unknown")
                _send_progress(task_id, filename, "cancelled")
                continue
            await _download_single(resource, api_key, task_id, cancel_event)
    finally:
        _active_downloads.pop(task_id, None)


@routes.post("/civitai/download")
async def handle_download(request):
    """
    POST /civitai/download

    Accepts: { "resource": {...}, "api_key": "sk_..." }
    Starts a background download for a single model.
    Returns: { "task_id": "uuid" }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    resource = data.get("resource")
    api_key = data.get("api_key", "")

    if not resource:
        return web.json_response({"error": "resource is required"}, status=400)
    if not api_key:
        return web.json_response({"error": "API key is required"}, status=401)

    task_id = str(uuid.uuid4())
    cancel_event = asyncio.Event()
    task = DownloadTask(task_id=task_id, cancel_event=cancel_event,
                        resources=[resource])

    coro = _run_single_download(resource, api_key, task_id, cancel_event)
    task.asyncio_task = asyncio.create_task(coro)
    _active_downloads[task_id] = task

    return web.json_response({"task_id": task_id})


@routes.post("/civitai/download-all")
async def handle_download_all(request):
    """
    POST /civitai/download-all

    Accepts: { "resources": [...], "api_key": "sk_..." }
    Starts background sequential download for multiple models.
    Returns: { "task_id": "uuid" }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    resources = data.get("resources", [])
    api_key = data.get("api_key", "")

    if not resources:
        return web.json_response({"error": "resources list is required"}, status=400)
    if not api_key:
        return web.json_response({"error": "API key is required"}, status=401)

    task_id = str(uuid.uuid4())
    cancel_event = asyncio.Event()
    task = DownloadTask(task_id=task_id, cancel_event=cancel_event,
                        resources=resources)

    coro = _run_batch_download(resources, api_key, task_id, cancel_event)
    task.asyncio_task = asyncio.create_task(coro)
    _active_downloads[task_id] = task

    return web.json_response({"task_id": task_id})


@routes.post("/civitai/download-cancel")
async def handle_download_cancel(request):
    """
    POST /civitai/download-cancel

    Accepts: { "task_id": "uuid" } or { "cancel_all": true }
    Signals cancellation; the download loop will stop on the next chunk.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    cancel_all = data.get("cancel_all", False)
    task_id = data.get("task_id")

    if cancel_all:
        for dt in list(_active_downloads.values()):
            dt.cancel_event.set()
        return web.json_response({"cancelled": True})

    if not task_id:
        return web.json_response({"error": "task_id is required"}, status=400)

    dt = _active_downloads.get(task_id)
    if dt:
        dt.cancel_event.set()
        return web.json_response({"cancelled": True})

    return web.json_response({"error": "Task not found"}, status=404)


# ── Workflow generation ──────────────────────────────────────────────


@routes.post("/civitai/generate")
async def handle_generate_workflow(request):
    """
    POST /civitai/generate

    Accepts: { "metadata": {...}, "resources": {...} }
    Returns: { "workflow": {...}, "workflow_type": "txt2img"|"txt2img-hires", "node_count": N }

    Reuses pipeline/generate_workflow.py's build_workflow() to produce
    a ComfyUI API-format workflow from metadata and resolved resources.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"error": "Invalid JSON in request body"},
            status=400,
        )

    metadata = data.get("metadata")
    resources = data.get("resources")

    if not metadata:
        return web.json_response(
            {"error": "metadata is required"},
            status=400,
        )

    if resources is None:
        return web.json_response(
            {"error": "resources is required"},
            status=400,
        )

    # resources may be a list (from frontend) or a dict with "resources" key
    # build_workflow expects { "resources": [...] }
    if isinstance(resources, list):
        resources_dict = {"resources": resources}
    elif isinstance(resources, dict) and "resources" in resources:
        resources_dict = resources
    else:
        return web.json_response(
            {"error": "resources must be a list or object with 'resources' key"},
            status=400,
        )

    try:
        workflow = build_workflow(metadata, resources_dict)
    except ValueError as e:
        return web.json_response(
            {"error": str(e)},
            status=422,
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Workflow generation failed: {e}"},
            status=500,
        )

    # Determine workflow type
    workflow_type = metadata.get("workflow_type", "txt2img")

    return web.json_response({
        "workflow": workflow,
        "workflow_type": workflow_type,
        "node_count": len(workflow),
    })
