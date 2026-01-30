"""
Download Models

Downloads resolved model files to the correct ComfyUI directories.

Usage:
    python -m pipeline.download_models
    python -m pipeline.download_models --dry-run
    python -m pipeline.download_models --input output/resources.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.model_manager import ModelManager


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Download model files to ComfyUI")
    parser.add_argument("--input", "-i", default="output/resources.json",
                        help="Input resources JSON file")
    parser.add_argument("--comfyui-path", default=None,
                        help="Path to ComfyUI installation")
    parser.add_argument("--api-key", default=None,
                        help="Civitai API key (or set CIVITAI_API_KEY env var)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without downloading")
    args = parser.parse_args()

    # Load resources
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run resolve_models first.", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])
    to_download = [r for r in resources if r.get("resolved") and not r.get("already_downloaded")]

    if not to_download:
        print("All models are already downloaded. Nothing to do.")
        sys.exit(0)

    # Summary
    total_mb = sum((r.get("size_kb") or 0) / 1024 for r in to_download)
    print(f"Models to download: {len(to_download)}")
    print(f"Total size: {total_mb:.1f} MB\n")

    for r in to_download:
        size_mb = (r.get("size_kb") or 0) / 1024
        print(f"  [{r['type']}] {r['filename']} ({size_mb:.1f} MB) -> {r['target_dir']}/")

    if args.dry_run:
        print("\n(dry run - no files downloaded)")
        sys.exit(0)

    print()

    # Initialize
    api_key = args.api_key or os.environ.get("CIVITAI_API_KEY")
    manager = ModelManager(comfyui_path=args.comfyui_path)

    # Download each model
    succeeded = []
    failed = []

    for r in to_download:
        print(f"Downloading {r['filename']}...")
        target = Path(r["target_path"])

        try:
            actual_path = manager.download_file(
                url=r["download_url"],
                destination=target,
                api_key=api_key,
            )
            print(f"  Saved to {actual_path}\n")
            r["already_downloaded"] = True
            r["target_path"] = str(actual_path)
            succeeded.append(r)
        except Exception as e:
            print(f"  FAILED: {e}\n", file=sys.stderr)
            r["error"] = str(e)
            failed.append(r)

    # Update resources file
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Final summary
    print(f"--- Download Summary ---")
    print(f"Succeeded: {len(succeeded)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed downloads:")
        for r in failed:
            print(f"  - {r['filename']}: {r.get('error', 'unknown error')}")
        sys.exit(1)

    print("\nAll downloads completed successfully.")


if __name__ == "__main__":
    main()
