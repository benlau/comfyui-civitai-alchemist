"""
Generate Workflow

Builds a ComfyUI API-format workflow JSON from image metadata and
resolved resources, and optionally submits it to a running ComfyUI instance.

Usage:
    python -m pipeline.generate_workflow
    python -m pipeline.generate_workflow --submit
    python -m pipeline.generate_workflow --metadata output/metadata.json --resources output/resources.json
"""

import argparse
import json
import sys
from pathlib import Path
from urllib import request as urllib_request

from pipeline.sampler_map import map_sampler


def build_workflow(metadata: dict, resources: dict) -> dict:
    """
    Build a ComfyUI API-format workflow from metadata and resources.

    Supports txt2img with optional LoRA(s).

    Args:
        metadata: Image metadata from fetch_metadata
        resources: Resolved resources from resolve_models

    Returns:
        ComfyUI workflow dictionary (API format)
    """
    prompt_text = metadata.get("prompt", "")
    negative_prompt = metadata.get("negative_prompt", "")
    steps = metadata.get("steps") or 20
    cfg_scale = metadata.get("cfg_scale") or 7.0
    seed = metadata.get("seed") or 0
    width = metadata.get("size", {}).get("width", 512)
    height = metadata.get("size", {}).get("height", 512)

    # Map sampler
    civitai_sampler = metadata.get("sampler", "Euler")
    schedule_type = metadata.get("raw_meta", {}).get("Schedule type")
    sampler_name, scheduler = map_sampler(civitai_sampler, schedule_type)

    # Find checkpoint filename from resources
    resource_list = resources.get("resources", [])
    checkpoint_filename = None
    lora_resources = []

    for r in resource_list:
        if not r.get("resolved"):
            continue
        if r["type"] == "checkpoint" and r.get("filename"):
            checkpoint_filename = r["filename"]
        elif r["type"] == "lora" and r.get("filename"):
            lora_resources.append(r)

    if not checkpoint_filename:
        # Fallback: use model_name from metadata to guess filename
        model_name = metadata.get("model_name", "")
        if model_name:
            checkpoint_filename = f"{model_name}.safetensors"
            print(f"Warning: No checkpoint resolved, guessing filename: {checkpoint_filename}")
        else:
            print("Error: No checkpoint model found in resources", file=sys.stderr)
            sys.exit(1)

    # Build the workflow
    workflow = {}

    # Node 1: CheckpointLoaderSimple
    workflow["1"] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": checkpoint_filename,
        },
    }

    # Track which node provides MODEL and CLIP
    # After checkpoint loader: model=["1",0], clip=["1",1], vae=["1",2]
    model_source = ["1", 0]
    clip_source = ["1", 1]
    vae_source = ["1", 2]

    # Insert LoRA loaders (chained)
    lora_node_id = 10
    for lora in lora_resources:
        node_id = str(lora_node_id)
        weight = lora.get("weight") or 1.0
        workflow[node_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora["filename"],
                "strength_model": weight,
                "strength_clip": weight,
                "model": model_source,
                "clip": clip_source,
            },
        }
        # Update sources to chain from this LoRA node
        model_source = [node_id, 0]
        clip_source = [node_id, 1]
        lora_node_id += 1

    # Node 2: CLIPTextEncode (positive prompt)
    workflow["2"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": prompt_text,
            "clip": clip_source,
        },
    }

    # Node 3: CLIPTextEncode (negative prompt)
    workflow["3"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": negative_prompt,
            "clip": clip_source,
        },
    }

    # Node 4: EmptyLatentImage
    workflow["4"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "width": width,
            "height": height,
        },
    }

    # Node 5: KSampler
    workflow["5"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_source,
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["4", 0],
            "seed": seed,
            "steps": steps,
            "cfg": cfg_scale,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "denoise": 1.0,
        },
    }

    # Node 6: VAEDecode
    workflow["6"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["5", 0],
            "vae": vae_source,
        },
    }

    # Node 7: SaveImage
    image_id = metadata.get("image_id", "unknown")
    workflow["7"] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": f"civitai_{image_id}",
            "images": ["6", 0],
        },
    }

    return workflow


def submit_workflow(workflow: dict, comfyui_url: str) -> bool:
    """
    Submit a workflow to a running ComfyUI instance.

    Args:
        workflow: ComfyUI API-format workflow
        comfyui_url: ComfyUI server URL (e.g. http://127.0.0.1:8188)

    Returns:
        True if submission succeeded
    """
    payload = {"prompt": workflow}
    data = json.dumps(payload).encode("utf-8")

    url = f"{comfyui_url}/prompt"
    req = urllib_request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        response = urllib_request.urlopen(req)
        result = json.loads(response.read())
        prompt_id = result.get("prompt_id", "unknown")
        print(f"Workflow submitted successfully! Prompt ID: {prompt_id}")
        return True
    except Exception as e:
        print(f"Error submitting workflow: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate ComfyUI workflow from metadata")
    parser.add_argument("--metadata", "-m", default="output/metadata.json",
                        help="Input metadata JSON file")
    parser.add_argument("--resources", "-r", default="output/resources.json",
                        help="Input resources JSON file")
    parser.add_argument("--output", "-o", default="output/workflow.json",
                        help="Output workflow JSON file")
    parser.add_argument("--submit", action="store_true",
                        help="Submit workflow to running ComfyUI instance")
    parser.add_argument("--comfyui-url", default="http://127.0.0.1:8188",
                        help="ComfyUI server URL")
    args = parser.parse_args()

    # Load inputs
    metadata_path = Path(args.metadata)
    resources_path = Path(args.resources)

    if not metadata_path.exists():
        print(f"Error: {metadata_path} not found. Run fetch_metadata first.", file=sys.stderr)
        sys.exit(1)
    if not resources_path.exists():
        print(f"Error: {resources_path} not found. Run resolve_models first.", file=sys.stderr)
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open(resources_path, "r", encoding="utf-8") as f:
        resources = json.load(f)

    # Build workflow
    print("Building workflow...")
    workflow = build_workflow(metadata, resources)

    # Print summary
    node_types = [n["class_type"] for n in workflow.values()]
    print(f"Nodes: {len(workflow)}")
    for nid, node in sorted(workflow.items(), key=lambda x: int(x[0])):
        print(f"  [{nid}] {node['class_type']}")

    sampler_node = workflow.get("5", {}).get("inputs", {})
    print(f"\nSampler: {sampler_node.get('sampler_name')} / {sampler_node.get('scheduler')}")
    print(f"Steps: {sampler_node.get('steps')}, CFG: {sampler_node.get('cfg')}, Seed: {sampler_node.get('seed')}")

    ckpt = workflow.get("1", {}).get("inputs", {}).get("ckpt_name", "?")
    print(f"Checkpoint: {ckpt}")

    lora_nodes = [n for n in workflow.values() if n["class_type"] == "LoraLoader"]
    if lora_nodes:
        print(f"LoRAs: {len(lora_nodes)}")
        for n in lora_nodes:
            inputs = n["inputs"]
            print(f"  - {inputs['lora_name']} (weight: {inputs['strength_model']})")

    # Save workflow
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)

    print(f"\nWorkflow saved to {output_path}")

    # Submit if requested
    if args.submit:
        print(f"\nSubmitting to {args.comfyui_url}...")
        success = submit_workflow(workflow, args.comfyui_url)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
