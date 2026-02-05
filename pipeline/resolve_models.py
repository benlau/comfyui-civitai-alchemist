"""
Resolve Models

Takes metadata.json and resolves each resource to a downloadable model
with version info, download URL, and local target path.

Usage:
    python -m pipeline.resolve_models
    python -m pipeline.resolve_models --input output/metadata.json --output output/resources.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("civitai_alchemist.resolve")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

sys.path.insert(0, str(Path(__file__).parent.parent))

from civitai_utils.civitai_api import CivitaiAPI
from civitai_utils.model_manager import ModelManager


def resolve_resource(resource: dict, api: CivitaiAPI, manager: ModelManager,
                     debug_data: dict = None) -> dict:
    """
    Resolve a single resource to its download information.

    Resolution strategies (in order):
      0. model_version_id lookup (primary — tRPC resources always have this)
      1. Hash lookup (fallback for meta.resources)
      2. Name search (last resort)

    Args:
        resource: Resource dict from metadata (name, type, weight, hash,
                  and usually model_version_id from tRPC)
        api: CivitaiAPI instance
        manager: ModelManager instance
        debug_data: Optional dict to record strategy attempts (for debug mode)

    Returns:
        Resolved resource dict with download info
    """
    result = {
        **resource,
        "model_id": None,
        "model_version_id": None,
        "download_url": None,
        "filename": None,
        "size_kb": None,
        "target_dir": None,
        "target_path": None,
        "already_downloaded": False,
        "resolved": False,
        "resolve_method": None,
        "error": None,
    }

    strategies_attempted = []

    model_type = resource.get("type", "checkpoint")
    result["target_dir"] = ModelManager.TYPE_MAPPING.get(model_type, model_type)

    # Strategy 0: Look up by model version ID (primary path for tRPC resources)
    version_id = resource.get("model_version_id")
    if version_id:
        print(f"  Looking up version ID: {version_id}...")
        try:
            version_data = api.get_model_version(version_id)
            if version_data:
                strategies_attempted.append({
                    "method": "version_id",
                    "version_id": version_id,
                    "status": "success",
                })
                logger.debug("[%s] Resolved via version_id=%d", resource.get("name"), version_id)
                if debug_data is not None:
                    debug_data["strategies_attempted"] = strategies_attempted
                return _fill_from_version_data(result, version_data, manager, "version_id")
            else:
                strategies_attempted.append({
                    "method": "version_id",
                    "version_id": version_id,
                    "status": "not_found",
                })
        except Exception as e:
            strategies_attempted.append({
                "method": "version_id",
                "version_id": version_id,
                "status": "error",
                "error": str(e),
            })
            print(f"  Version ID lookup failed: {e}")

    # Strategy 1: Look up by hash
    file_hash = resource.get("hash")
    if file_hash:
        print(f"  Looking up hash: {file_hash}...")
        try:
            version_data = api.get_model_version_by_hash(file_hash)
            if version_data:
                strategies_attempted.append({
                    "method": "hash",
                    "hash": file_hash,
                    "status": "success",
                })
                logger.debug("[%s] Resolved via hash=%s", resource.get("name"), file_hash)
                if debug_data is not None:
                    debug_data["strategies_attempted"] = strategies_attempted
                return _fill_from_version_data(result, version_data, manager, "hash")
            else:
                strategies_attempted.append({
                    "method": "hash",
                    "hash": file_hash,
                    "status": "not_found",
                })
        except Exception as e:
            strategies_attempted.append({
                "method": "hash",
                "hash": file_hash,
                "status": "error",
                "error": str(e),
            })
            print(f"  Hash lookup failed: {e}")

    # Strategy 2: Search by name
    name = resource.get("name", "")
    if name:
        print(f"  Searching by name: {name}...")
        try:
            models = api.search_models(name, limit=5)
            for model in models:
                # Find a matching model by name (case-insensitive partial match)
                model_name = model.get("name", "")
                if name.lower() in model_name.lower() or model_name.lower() in name.lower():
                    versions = model.get("modelVersions", [])
                    if versions:
                        strategies_attempted.append({
                            "method": "name_search",
                            "query": name,
                            "matched_model": model_name,
                            "status": "success",
                        })
                        logger.debug("[%s] Resolved via name_search, matched '%s'",
                                     resource.get("name"), model_name)
                        if debug_data is not None:
                            debug_data["strategies_attempted"] = strategies_attempted
                        return _fill_from_version_data(
                            result, versions[0], manager, "name_search",
                            model_id=model.get("id"),
                            model_type_override=model.get("type"),
                        )
            strategies_attempted.append({
                "method": "name_search",
                "query": name,
                "status": "no_match",
                "candidates": [m.get("name", "") for m in models[:5]],
            })
        except Exception as e:
            strategies_attempted.append({
                "method": "name_search",
                "query": name,
                "status": "error",
                "error": str(e),
            })
            print(f"  Name search failed: {e}")

    if debug_data is not None:
        debug_data["strategies_attempted"] = strategies_attempted

    result["error"] = "Could not resolve resource"
    return result


def _fill_from_version_data(
    result: dict,
    version_data: dict,
    manager: ModelManager,
    method: str,
    model_id: int = None,
    model_type_override: str = None,
) -> dict:
    """
    Fill result dict from a model version API response.

    Args:
        result: Result dict to fill
        version_data: Model version data from API
        manager: ModelManager instance
        method: How we resolved this ("hash" or "name_search")
        model_id: Override model ID (from search results)
        model_type_override: Override model type (from search results)
    """
    result["model_version_id"] = version_data.get("id")
    result["model_id"] = model_id or version_data.get("modelId")
    result["resolve_method"] = method

    # If no type override provided, try to get from version data
    if not model_type_override:
        model_info = version_data.get("model", {})
        if model_info.get("type"):
            model_type_override = model_info["type"]
        if model_info.get("id") and not result["model_id"]:
            result["model_id"] = model_info["id"]

    # Get the primary file
    files = version_data.get("files", [])
    primary_file = None
    for f in files:
        if f.get("primary", False):
            primary_file = f
            break
    if not primary_file and files:
        primary_file = files[0]

    if primary_file:
        result["filename"] = primary_file.get("name", "")
        result["size_kb"] = primary_file.get("sizeKB")
        result["download_url"] = primary_file.get("downloadUrl") or \
            f"https://civitai.com/api/download/models/{result['model_version_id']}"
        result["hashes"] = primary_file.get("hashes")

    # Override type if we got it from search
    if model_type_override:
        model_type = model_type_override
        # Normalize Civitai type names
        type_lower = model_type.lower()
        if type_lower in ("checkpoint", "model"):
            result["type"] = "checkpoint"
        elif type_lower in ("lora", "locon"):
            result["type"] = "lora"
        elif type_lower in ("textualinversion",):
            result["type"] = "embedding"
        elif type_lower in ("upscaler",):
            result["type"] = "upscaler"
        else:
            result["type"] = type_lower
        result["target_dir"] = ModelManager.TYPE_MAPPING.get(result["type"], model_type)

    # Set target path
    if result["filename"]:
        model_dir = manager.get_model_dir(result["type"])
        result["target_path"] = str(model_dir / result["filename"])

        # Check if already downloaded
        existing = manager.find_model(result["filename"], result["type"])
        if existing:
            result["already_downloaded"] = True
            result["target_path"] = str(existing)

    # Fill in name if still unknown (e.g. civitaiResources with no modelName)
    if result.get("name") in (None, "", "unknown"):
        model_info = version_data.get("model", {})
        model_name = model_info.get("name", "")
        if model_name:
            result["name"] = model_name
        elif result.get("filename"):
            # Use filename without extension as fallback
            result["name"] = Path(result["filename"]).stem

    result["resolved"] = True
    return result


def main():
    if load_dotenv:
        load_dotenv()

    parser = argparse.ArgumentParser(description="Resolve model resources to download URLs")
    parser.add_argument("--input", "-i", default="output/metadata.json",
                        help="Input metadata JSON file")
    parser.add_argument("--output", "-o", default="output/resources.json",
                        help="Output resources JSON file")
    parser.add_argument("--models-dir", default=None,
                        help="Path to ComfyUI models directory (default: ../ComfyUI/models)")
    parser.add_argument("--api-key", default=None,
                        help="Civitai API key (or set CIVITAI_API_KEY env var)")
    args = parser.parse_args()

    # Load metadata
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run fetch_metadata first.", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    resources = metadata.get("resources", [])
    if not resources:
        print("No resources found in metadata.")
        sys.exit(0)

    print(f"Resolving {len(resources)} resource(s)...\n")

    # Initialize
    api_key = args.api_key or os.environ.get("CIVITAI_API_KEY")
    api = CivitaiAPI(api_key=api_key)
    manager = ModelManager(models_dir=args.models_dir)

    # Resolve each resource
    resolved = []
    unresolved = []

    for r in resources:
        print(f"[{r['name']}] ({r['type']})")
        result = resolve_resource(r, api, manager)
        if result["resolved"]:
            resolved.append(result)
            status = "ALREADY DOWNLOADED" if result["already_downloaded"] else "RESOLVED"
            size_str = ""
            if result["size_kb"]:
                size_mb = result["size_kb"] / 1024
                size_str = f" ({size_mb:.1f} MB)"
            print(f"  -> {status}: {result['filename']}{size_str}")
        else:
            unresolved.append(result)
            print(f"  -> UNRESOLVED: {result['error']}")
        print()

    # Summary
    print(f"--- Summary ---")
    print(f"Resolved: {len(resolved)}")
    print(f"Unresolved: {len(unresolved)}")
    to_download = [r for r in resolved if not r["already_downloaded"]]
    print(f"Need download: {len(to_download)}")
    if to_download:
        total_mb = sum((r.get("size_kb") or 0) / 1024 for r in to_download)
        print(f"Total download size: {total_mb:.1f} MB")

    # Save output
    output_data = {
        "resources": resolved + unresolved,
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nResources saved to {output_path}")

    if unresolved:
        sys.exit(1)


if __name__ == "__main__":
    main()
