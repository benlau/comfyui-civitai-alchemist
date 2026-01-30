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
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path so we can import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.civitai_api import CivitaiAPI


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

    # Normalize resources: Civitai uses "model" type for checkpoints
    resources = []
    for r in meta.get("resources", []):
        resource_type = r.get("type", "unknown")
        if resource_type == "model":
            resource_type = "checkpoint"
        resources.append({
            "name": r.get("name", "unknown"),
            "type": resource_type,
            "weight": r.get("weight"),
            "hash": r.get("hash"),
        })

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
        "model_name": meta.get("Model", ""),
        "model_hash": meta.get("Model hash", ""),
        "clip_skip": meta.get("Clip skip"),
        "resources": resources,
        "raw_meta": meta,
    }


def main():
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
