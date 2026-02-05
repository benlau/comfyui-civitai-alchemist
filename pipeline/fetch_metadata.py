"""
Fetch Metadata

Fetches image generation metadata from a Civitai image URL.

Usage:
    python -m pipeline.fetch_metadata https://civitai.com/images/116872916
    python -m pipeline.fetch_metadata 116872916
    python -m pipeline.fetch_metadata https://civitai.com/images/116872916 --output my_metadata.json
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger("civitai_alchemist.fetch")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Add project root to path so we can import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from civitai_utils.civitai_api import CivitaiAPI


def parse_image_id(url_or_id: str) -> int:
    """
    Extract image ID from a Civitai URL or bare ID string.

    Args:
        url_or_id: Either a full URL or just the numeric ID

    Returns:
        Integer image ID

    Raises:
        ValueError: If the input cannot be parsed
    """
    # Try bare integer
    if url_or_id.isdigit():
        return int(url_or_id)

    # Try URL pattern: https://civitai.com/images/123456
    match = re.search(r"civitai\.com/images/(\d+)", url_or_id)
    if match:
        return int(match.group(1))

    raise ValueError(f"Cannot parse image ID from: {url_or_id}")


def extract_metadata(image_data: dict) -> dict:
    """
    Extract and normalize generation metadata from Civitai image data.

    Args:
        image_data: Raw image data from Civitai API

    Returns:
        Normalized metadata dictionary
    """
    meta = image_data.get("meta") or {}

    # Handle nested meta structure: sometimes meta contains a "meta" sub-key
    if "meta" in meta and isinstance(meta["meta"], dict):
        meta = meta["meta"]

    # Parse image size
    size_str = meta.get("Size", "")
    width, height = 512, 512  # defaults
    if "x" in size_str:
        parts = size_str.split("x")
        try:
            width, height = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass
    elif image_data.get("width") and image_data.get("height"):
        width = image_data["width"]
        height = image_data["height"]

    # Resources are populated by enrich_metadata() from the tRPC endpoint.
    # extract_metadata() no longer parses meta.resources or meta.civitaiResources
    # because tRPC provides superior data (modelVersionId, modelName, modelType,
    # modelId, baseModel). See docs/research/2026-02-01-civitai-api-resource-resolution/

    # Detect hires workflow and extract related fields
    workflow_type = meta.get("workflow")
    denoise = meta.get("denoise")
    upscalers = meta.get("upscalers", [])

    # For hires workflows, raw_meta width/height is the base (generation) size,
    # and image_data width/height is the final (upscaled) output size
    base_width, base_height = width, height
    if workflow_type and "hires" in str(workflow_type).lower():
        raw_w = meta.get("width")
        raw_h = meta.get("height")
        if raw_w and raw_h:
            base_width = int(raw_w)
            base_height = int(raw_h)
        if image_data.get("width") and image_data.get("height"):
            width = image_data["width"]
            height = image_data["height"]

    return {
        "image_id": image_data.get("id"),
        "image_url": image_data.get("url"),
        "prompt": meta.get("prompt", ""),
        "negative_prompt": meta.get("negativePrompt", ""),
        "sampler": meta.get("sampler", ""),
        "steps": meta.get("steps"),
        "cfg_scale": meta.get("cfgScale"),
        "seed": meta.get("seed"),
        "size": {"width": width, "height": height},
        "base_size": {"width": base_width, "height": base_height},
        "model_name": meta.get("Model", ""),
        "model_hash": meta.get("Model hash", ""),
        "clip_skip": meta.get("Clip skip") or meta.get("clipSkip"),
        "resources": [],
        "workflow_type": workflow_type,
        "denoise": denoise,
        "upscalers": upscalers,
        "raw_meta": meta,
    }


def enrich_metadata(metadata: dict, api, debug_data: dict = None) -> dict:
    """
    Populate metadata resources from Civitai's tRPC endpoint (primary source).

    Uses tRPC image.getGenerationData as the sole resource source. This endpoint
    returns canonical resource data with modelVersionId, modelName, modelType,
    modelId, and baseModel — even for hidden/obfuscated models.

    Fallback chain when tRPC has no resources:
      1. meta.civitaiResources (has modelVersionId + weight, lacks modelName)
      2. meta.resources (has filename + hash + weight, lacks modelVersionId)

    See docs/research/2026-02-01-civitai-api-resource-resolution/ for analysis.

    Args:
        metadata: Metadata dict from extract_metadata()
        api: CivitaiAPI instance (must be authenticated)
        debug_data: Optional dict to record enrichment decisions (for debug mode)

    Returns:
        Enriched metadata dict (modified in place and returned)
    """
    image_id = metadata.get("image_id")
    if not image_id:
        return metadata

    enrichment_source = None
    fallback_attempted = False

    # Try tRPC as primary source
    resources = _resources_from_trpc(metadata, api)

    if resources:
        enrichment_source = "trpc"
    else:
        fallback_attempted = True

        # Fallback to civitaiResources if tRPC returned nothing
        raw_meta = metadata.get("raw_meta", {})
        resources = _resources_from_civitai_resources(raw_meta)

        if resources:
            enrichment_source = "civitaiResources"
        else:
            # Fallback to meta.resources if civitaiResources also empty
            resources = _resources_from_meta_resources(raw_meta)
            enrichment_source = "meta_resources" if resources else "none"

    metadata["resources"] = resources

    # Fix metadata-level model_name if it was unknown/empty
    if metadata.get("model_name", "").lower() in ("unknown_model", "unknown", ""):
        for r in resources:
            if r.get("type") == "checkpoint" and r.get("name"):
                metadata["model_name"] = r["name"]
                break

    logger.debug("Enrichment source: %s, fallback_attempted: %s, resources: %d",
                 enrichment_source, fallback_attempted, len(resources))

    if debug_data is not None:
        debug_data["enrichment"] = {
            "source": enrichment_source,
            "fallback_attempted": fallback_attempted,
        }
        debug_data["resource_count"] = len(resources)

    return metadata


# Civitai modelType -> normalized type used throughout the codebase
_TYPE_NORMALIZE = {
    "Checkpoint": "checkpoint",
    "checkpoint": "checkpoint",
    "model": "checkpoint",
    "LORA": "lora",
    "Lora": "lora",
    "lora": "lora",
    "LoCon": "lora",
    "locon": "lora",
    "lycoris": "lora",
    "TextualInversion": "embedding",
    "textualinversion": "embedding",
    "embed": "embedding",
    "Upscaler": "upscaler",
    "upscaler": "upscaler",
    "VAE": "vae",
    "vae": "vae",
}


def _normalize_type(raw_type: str) -> str:
    """Normalize a Civitai model type string to our internal type names."""
    return _TYPE_NORMALIZE.get(raw_type, raw_type.lower())


def _resources_from_trpc(metadata: dict, api) -> list:
    """
    Build resource list from tRPC image.getGenerationData endpoint.

    For LoRA resources with null strength, falls back to 1.0.
    """
    image_id = metadata.get("image_id")
    try:
        gen_data = api.get_image_generation_data(image_id)
    except Exception as e:
        print(f"  tRPC fetch failed: {e}")
        return []

    if not gen_data:
        return []

    trpc_resources = gen_data.get("resources", [])
    if not trpc_resources:
        return []

    resources = []
    for r in trpc_resources:
        version_id = r.get("modelVersionId")
        if not version_id:
            continue

        res_type = _normalize_type(r.get("modelType", ""))
        strength = r.get("strength")

        # LoRA with null strength defaults to 1.0
        if strength is None and res_type == "lora":
            strength = 1.0

        resources.append({
            "name": r.get("modelName", "unknown"),
            "type": res_type,
            "weight": strength,
            "hash": None,
            "model_version_id": version_id,
        })

    return resources


def _resources_from_civitai_resources(raw_meta: dict) -> list:
    """
    Build resource list from REST meta.civitaiResources (fallback #1).

    Has modelVersionId and weight but lacks modelName.
    Deduplicates by modelVersionId.
    """
    civitai_resources = raw_meta.get("civitaiResources", [])
    if not civitai_resources:
        return []

    resources = []
    seen_version_ids = {}
    for cr in civitai_resources:
        version_id = cr.get("modelVersionId")
        res_type = _normalize_type(cr.get("type", "unknown"))
        weight = cr.get("weight")

        # LoRA with null weight defaults to 1.0
        if weight is None and res_type == "lora":
            weight = 1.0

        entry = {
            "name": cr.get("modelName", "unknown"),
            "type": res_type,
            "weight": weight,
            "hash": None,
            "model_version_id": version_id,
        }

        # Deduplicate: keep the more informative entry for same version_id
        if version_id and version_id in seen_version_ids:
            existing_idx = seen_version_ids[version_id]
            existing_entry = resources[existing_idx]
            if existing_entry["type"] == "unknown" and res_type != "unknown":
                resources[existing_idx] = entry
            continue

        resources.append(entry)
        if version_id:
            seen_version_ids[version_id] = len(resources) - 1

    return resources


def _resources_from_meta_resources(raw_meta: dict) -> list:
    """
    Build resource list from REST meta.resources (fallback #2).

    Has filename and hash but lacks modelVersionId.
    """
    meta_resources = raw_meta.get("resources", [])
    if not meta_resources:
        return []

    # Build a hash lookup from the hashes dict (e.g. "LORA:name" -> "hash")
    hashes = raw_meta.get("hashes", {})
    lora_hash_map = {}
    for key, value in hashes.items():
        if key.startswith("LORA:"):
            lora_name = key[len("LORA:"):]
            lora_hash_map[lora_name] = value

    resources = []
    for r in meta_resources:
        res_type = _normalize_type(r.get("type", "unknown"))
        resource_hash = r.get("hash")
        # Fill in LoRA hash from hashes dict if not present
        if not resource_hash and res_type == "lora":
            resource_hash = lora_hash_map.get(r.get("name", ""))

        weight = r.get("weight")
        # LoRA with null weight defaults to 1.0
        if weight is None and res_type == "lora":
            weight = 1.0

        resources.append({
            "name": r.get("name", "unknown"),
            "type": res_type,
            "weight": weight,
            "hash": resource_hash,
        })

    return resources


def main():
    if load_dotenv:
        load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch image metadata from Civitai")
    parser.add_argument("url", help="Civitai image URL or image ID")
    parser.add_argument("--output", "-o", default="output/metadata.json",
                        help="Output JSON file path (default: output/metadata.json)")
    parser.add_argument("--api-key", default=None,
                        help="Civitai API key (or set CIVITAI_API_KEY env var)")
    args = parser.parse_args()

    # Parse image ID
    try:
        image_id = parse_image_id(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching metadata for image {image_id}...")

    # Initialize API client
    api_key = args.api_key or os.environ.get("CIVITAI_API_KEY")
    api = CivitaiAPI(api_key=api_key)

    # Fetch image data
    try:
        image_data = api.get_image_metadata(image_id)
    except Exception as e:
        print(f"Error fetching image data: {e}", file=sys.stderr)
        sys.exit(1)

    if image_data is None:
        print(f"Error: Image {image_id} not found on Civitai", file=sys.stderr)
        sys.exit(1)

    # Extract metadata
    metadata = extract_metadata(image_data)
    metadata = enrich_metadata(metadata, api)

    # Print summary
    print(f"\n--- Image {metadata['image_id']} ---")
    print(f"Model: {metadata['model_name']}")
    print(f"Sampler: {metadata['sampler']}, Steps: {metadata['steps']}, CFG: {metadata['cfg_scale']}")
    print(f"Seed: {metadata['seed']}")
    print(f"Size: {metadata['size']['width']}x{metadata['size']['height']}")
    print(f"Prompt: {metadata['prompt'][:100]}{'...' if len(metadata['prompt']) > 100 else ''}")
    if metadata['negative_prompt']:
        np = metadata['negative_prompt']
        print(f"Negative: {np[:80]}{'...' if len(np) > 80 else ''}")
    print(f"Resources: {len(metadata['resources'])}")
    for r in metadata['resources']:
        weight_str = f" (weight: {r['weight']})" if r['weight'] is not None else ""
        hash_str = f" [hash: {r['hash']}]" if r['hash'] else ""
        print(f"  - {r['name']} ({r['type']}){weight_str}{hash_str}")

    if not metadata['prompt']:
        print("\nWarning: No generation prompt found in metadata", file=sys.stderr)

    # Save to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nMetadata saved to {output_path}")


if __name__ == "__main__":
    main()
