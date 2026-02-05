"""
Reproduce

End-to-end runner that fetches metadata, resolves models, downloads them,
and generates a ComfyUI workflow from a Civitai image URL.

Usage:
    python -m pipeline.reproduce https://civitai.com/images/116872916
    python -m pipeline.reproduce https://civitai.com/images/116872916 --submit
    python -m pipeline.reproduce https://civitai.com/images/116872916 --skip-download
    python -m pipeline.reproduce https://civitai.com/images/116872916 --debug
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.fetch_metadata import parse_image_id, extract_metadata, enrich_metadata
from pipeline.resolve_models import resolve_resource
from pipeline.generate_workflow import build_workflow, submit_workflow
from civitai_utils.civitai_api import CivitaiAPI
from civitai_utils.model_manager import ModelManager


def main():
    if load_dotenv:
        load_dotenv()

    parser = argparse.ArgumentParser(
        description="Reproduce a Civitai image locally via ComfyUI"
    )
    parser.add_argument("url", help="Civitai image URL or image ID")
    parser.add_argument("--output-dir", default="output",
                        help="Output directory for JSON files (default: output)")
    parser.add_argument("--models-dir", default=None,
                        help="Path to ComfyUI models directory (default: ../ComfyUI/models)")
    parser.add_argument("--api-key", default=None,
                        help="Civitai API key (or set CIVITAI_API_KEY env var)")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip downloading models")
    parser.add_argument("--submit", action="store_true",
                        help="Submit workflow to running ComfyUI instance")
    parser.add_argument("--comfyui-url", default="http://127.0.0.1:8188",
                        help="ComfyUI server URL")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode: verbose logging to stderr, "
                             "saves debug_report.json, skips download and submit")
    args = parser.parse_args()

    # Debug mode setup
    debug_mode = args.debug
    debug_report = None
    api_log = None
    overall_start = None

    if debug_mode:
        from pipeline.debug import (
            configure_debug_logging, create_debug_report, save_debug_report,
        )
        configure_debug_logging()
        debug_report = create_debug_report(args.url, args)
        api_log = debug_report["api_calls"]
        overall_start = time.monotonic()
        # Debug mode auto-skips download and submit
        args.skip_download = True
        args.submit = False

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = args.api_key or os.environ.get("CIVITAI_API_KEY")
    api = CivitaiAPI(api_key=api_key, api_log=api_log)
    manager = ModelManager(models_dir=args.models_dir)

    if debug_report:
        debug_report["environment"]["models_dir"] = str(manager.models_path)
        debug_report["environment"]["models_dir_exists"] = manager.models_path.exists()
        debug_report["environment"]["api_key_present"] = bool(api_key)

    # === Step 1: Fetch Metadata ===
    print("=" * 50)
    print("Step 1: Fetching metadata")
    print("=" * 50)

    step1_data = {}
    step1_start = time.monotonic() if debug_mode else 0

    try:
        image_id = parse_image_id(args.url)
    except ValueError as e:
        if debug_report:
            debug_report["errors"].append({
                "step": "parse_url", "error": str(e),
                "traceback": traceback.format_exc(),
            })
            save_debug_report(debug_report, output_dir)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if debug_report:
        debug_report["image_id"] = image_id

    print(f"Image ID: {image_id}")

    try:
        image_data = api.get_image_metadata(image_id)
    except Exception as e:
        if debug_report:
            debug_report["errors"].append({
                "step": "fetch_metadata", "error": str(e),
                "traceback": traceback.format_exc(),
            })
            save_debug_report(debug_report, output_dir)
        print(f"Error fetching metadata: {e}", file=sys.stderr)
        sys.exit(1)

    if image_data is None:
        if debug_report:
            debug_report["errors"].append({
                "step": "fetch_metadata",
                "error": f"Image {image_id} not found",
            })
            save_debug_report(debug_report, output_dir)
        print(f"Error: Image {image_id} not found", file=sys.stderr)
        sys.exit(1)

    if debug_mode:
        step1_data["raw_image_data"] = image_data

    metadata = extract_metadata(image_data)
    metadata = enrich_metadata(
        metadata, api,
        debug_data=step1_data if debug_mode else None,
    )

    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    if debug_report:
        step1_data["status"] = "success"
        step1_data["duration_ms"] = round((time.monotonic() - step1_start) * 1000)
        step1_data["result"] = metadata
        debug_report["steps"]["fetch_metadata"] = step1_data

    print(f"Model: {metadata['model_name']}")
    print(f"Sampler: {metadata['sampler']}, Steps: {metadata['steps']}, CFG: {metadata['cfg_scale']}")
    print(f"Size: {metadata['size']['width']}x{metadata['size']['height']}")
    if metadata.get("workflow_type"):
        print(f"Workflow: {metadata['workflow_type']}")
    if metadata.get("base_size") and metadata["base_size"] != metadata["size"]:
        bs = metadata["base_size"]
        print(f"Base size: {bs['width']}x{bs['height']}")
    print(f"Resources: {len(metadata['resources'])}")
    print(f"Saved to {metadata_path}\n")

    # === Step 2: Resolve Models ===
    print("=" * 50)
    print("Step 2: Resolving models")
    print("=" * 50)

    step2_data = {"resources": []}
    step2_start = time.monotonic() if debug_mode else 0

    resources_list = metadata.get("resources", [])
    resolved = []
    unresolved = []

    for r in resources_list:
        print(f"[{r['name']}] ({r['type']})")
        resource_debug = {} if debug_mode else None
        result = resolve_resource(
            r, api, manager,
            debug_data=resource_debug,
        )
        if debug_mode:
            resource_debug["input"] = r
            resource_debug["result"] = result
            step2_data["resources"].append(resource_debug)
        if result["resolved"]:
            resolved.append(result)
            status = "ALREADY DOWNLOADED" if result["already_downloaded"] else "RESOLVED"
            print(f"  -> {status}: {result.get('filename', '?')}")
        else:
            unresolved.append(result)
            print(f"  -> UNRESOLVED: {result.get('error', '?')}")

    resources_data = {
        "resources": resolved + unresolved,
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
    }

    resources_path = output_dir / "resources.json"
    with open(resources_path, "w", encoding="utf-8") as f:
        json.dump(resources_data, f, indent=2, ensure_ascii=False)

    if debug_report:
        step2_data["status"] = "success"
        step2_data["duration_ms"] = round((time.monotonic() - step2_start) * 1000)
        step2_data["resolved_count"] = len(resolved)
        step2_data["unresolved_count"] = len(unresolved)
        debug_report["steps"]["resolve_models"] = step2_data

    print(f"\nResolved: {len(resolved)}, Unresolved: {len(unresolved)}")
    print(f"Saved to {resources_path}\n")

    # === Step 3: Download Models ===
    if debug_mode:
        print("Step 3: Skipped (--debug mode)\n")
        if debug_report:
            debug_report["steps"]["download_models"] = {
                "status": "skipped_debug_mode",
                "duration_ms": 0,
            }
    elif not args.skip_download:
        print("=" * 50)
        print("Step 3: Downloading models")
        print("=" * 50)

        to_download = [r for r in resolved if not r.get("already_downloaded")]
        if not to_download:
            print("All models already downloaded.\n")
        else:
            total_mb = sum((r.get("size_kb") or 0) / 1024 for r in to_download)
            print(f"Downloading {len(to_download)} file(s) ({total_mb:.1f} MB total)\n")

            for r in to_download:
                print(f"Downloading {r['filename']}...")
                try:
                    actual_path = manager.download_file(
                        url=r["download_url"],
                        destination=Path(r["target_path"]),
                        api_key=api_key,
                    )
                    r["already_downloaded"] = True
                    r["target_path"] = str(actual_path)
                    print(f"  Done: {actual_path}\n")
                except Exception as e:
                    print(f"  FAILED: {e}\n", file=sys.stderr)

            # Update resources file
            with open(resources_path, "w", encoding="utf-8") as f:
                json.dump(resources_data, f, indent=2, ensure_ascii=False)
    else:
        print("Step 3: Skipped (--skip-download)\n")

    # === Step 4: Generate Workflow ===
    print("=" * 50)
    print("Step 4: Generating workflow")
    print("=" * 50)

    step4_data = {}
    step4_start = time.monotonic() if debug_mode else 0

    try:
        workflow = build_workflow(
            metadata, resources_data,
            debug_data=step4_data if debug_mode else None,
        )
    except Exception as e:
        if debug_report:
            step4_data["status"] = "failed"
            step4_data["error"] = str(e)
            step4_data["traceback"] = traceback.format_exc()
            step4_data["duration_ms"] = round((time.monotonic() - step4_start) * 1000)
            debug_report["steps"]["generate_workflow"] = step4_data
            debug_report["errors"].append({
                "step": "generate_workflow", "error": str(e),
                "traceback": traceback.format_exc(),
            })
            debug_report["total_duration_ms"] = round(
                (time.monotonic() - overall_start) * 1000
            )
            save_debug_report(debug_report, output_dir)
        print(f"Error generating workflow: {e}", file=sys.stderr)
        sys.exit(1)

    workflow_path = output_dir / "workflow.json"
    with open(workflow_path, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)

    if debug_report:
        step4_data["status"] = "success"
        step4_data["duration_ms"] = round((time.monotonic() - step4_start) * 1000)
        step4_data["node_count"] = len(workflow)
        debug_report["steps"]["generate_workflow"] = step4_data

    print(f"Workflow nodes: {len(workflow)}")
    for nid, node in sorted(workflow.items(), key=lambda x: int(x[0])):
        print(f"  [{nid}] {node['class_type']}")

    print(f"Saved to {workflow_path}\n")

    # === Step 5: Submit (optional) ===
    if args.submit:
        print("=" * 50)
        print("Step 5: Submitting to ComfyUI")
        print("=" * 50)
        success = submit_workflow(workflow, args.comfyui_url)
        if not success:
            sys.exit(1)
        print()

    # === Save debug report ===
    if debug_report:
        debug_report["total_duration_ms"] = round(
            (time.monotonic() - overall_start) * 1000
        )
        save_debug_report(debug_report, output_dir)

    # === Summary ===
    print("=" * 50)
    print("Done!")
    print("=" * 50)
    print(f"  Metadata:  {metadata_path}")
    print(f"  Resources: {resources_path}")
    print(f"  Workflow:  {workflow_path}")
    if debug_mode:
        print(f"  Debug:     {output_dir / 'debug_report.json'} (summary)")
        print(f"  Debug:     {output_dir / 'debug_report_full.json'} (full)")
    if not args.submit and not debug_mode:
        print(f"\nTo submit to ComfyUI, run:")
        print(f"  python -m pipeline.generate_workflow --submit")


if __name__ == "__main__":
    main()
