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
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.civitai_api import CivitaiAPI
from utils.model_manager import ModelManager


def resolve_resource(resource: dict, api: CivitaiAPI, manager: ModelManager) -> dict:
    """
    Resolve a single resource to its download information.

    Tries hash lookup first, then falls back to name search.

    Args:
        resource: Resource dict from metadata (name, type, weight, hash)
        api: CivitaiAPI instance
        manager: ModelManager instance

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

    model_type = resource.get("type", "checkpoint")
    result["target_dir"] = ModelManager.TYPE_MAPPING.get(model_type, model_type)

    # Strategy 1: Look up by hash
    file_hash = resource.get("hash")
    if file_hash:
        print(f"  Looking up hash: {file_hash}...")
        try:
            version_data = api.get_model_version_by_hash(file_hash)
            if version_data:
                return _fill_from_version_data(result, version_data, manager, "hash")
        except Exception as e:
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
                        return _fill_from_version_data(
                            result, versions[0], manager, "name_search",
                            model_id=model.get("id"),
                            model_type_override=model.get("type"),
                        )
        except Exception as e:
            print(f"  Name search failed: {e}")

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
        else:
            result["type"] = type_lower
        result["target_dir"] = ModelManager.TYPE_MAPPING.get(model_type, model_type)

    # Set target path
    if result["filename"]:
        model_dir = manager.get_model_dir(result["type"])
        result["target_path"] = str(model_dir / result["filename"])

        # Check if already downloaded
        existing = manager.find_model(result["filename"], result["type"])
        if existing:
            result["already_downloaded"] = True
            result["target_path"] = str(existing)

    result["resolved"] = True
    return result


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Resolve model resources to download URLs")
    parser.add_argument("--input", "-i", default="output/metadata.json",
                        help="Input metadata JSON file")
    parser.add_argument("--output", "-o", default="output/resources.json",
                        help="Output resources JSON file")
    parser.add_argument("--comfyui-path", default=None,
                        help="Path to ComfyUI installation")
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
    manager = ModelManager(comfyui_path=args.comfyui_path)

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
