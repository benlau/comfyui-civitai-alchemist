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
import random
import re
import sys
from pathlib import Path
from urllib import request as urllib_request

from pipeline.sampler_map import map_sampler


def build_workflow(metadata: dict, resources: dict) -> dict:
    """
    Build a ComfyUI API-format workflow from metadata and resources.

    Dispatches to appropriate builder based on workflow type.

    Args:
        metadata: Image metadata from fetch_metadata
        resources: Resolved resources from resolve_models

    Returns:
        ComfyUI workflow dictionary (API format)
    """
    workflow_type = metadata.get("workflow_type", "")
    if workflow_type and "hires" in str(workflow_type).lower():
        return _build_hires_workflow(metadata, resources)
    return _build_txt2img_workflow(metadata, resources)


def _extract_common_params(metadata: dict, resources: dict) -> dict:
    """
    Extract common parameters shared by all workflow builders.

    Returns:
        Dict with prompt, negative_prompt, steps, cfg_scale, seed,
        sampler_name, scheduler, checkpoint_filename, lora_resources,
        upscaler_filename, clip_skip.
    """
    prompt_text = metadata.get("prompt", "")
    # Strip <lora:name:weight> tags — ComfyUI uses LoraLoader nodes instead
    prompt_text = re.sub(r"\s*<lora:[^>]+>", "", prompt_text)
    negative_prompt = metadata.get("negative_prompt", "")
    steps = metadata.get("steps") or 20
    cfg_scale = metadata.get("cfg_scale") or 7.0
    seed = metadata.get("seed")
    if seed is None:
        seed = random.randint(0, 2**63 - 1)

    # Map sampler
    civitai_sampler = metadata.get("sampler", "Euler")
    schedule_type = metadata.get("raw_meta", {}).get("Schedule type")
    sampler_name, scheduler = map_sampler(civitai_sampler, schedule_type)

    # Find resources from resolved list
    resource_list = resources.get("resources", [])
    checkpoint_filename = None
    lora_resources = []
    upscaler_filename = None

    for r in resource_list:
        if not r.get("resolved"):
            continue
        if r["type"] == "checkpoint" and r.get("filename"):
            checkpoint_filename = r["filename"]
        elif r["type"] == "lora" and r.get("filename"):
            lora_resources.append(r)
        elif r["type"] == "upscaler" and r.get("filename"):
            upscaler_filename = r["filename"]

    if not checkpoint_filename:
        model_name = metadata.get("model_name", "")
        if model_name:
            checkpoint_filename = f"{model_name}.safetensors"
            print(f"Warning: No checkpoint resolved, guessing filename: {checkpoint_filename}")
        else:
            print("Error: No checkpoint model found in resources", file=sys.stderr)
            sys.exit(1)

    clip_skip = metadata.get("clip_skip")

    return {
        "prompt_text": prompt_text,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "seed": seed,
        "sampler_name": sampler_name,
        "scheduler": scheduler,
        "checkpoint_filename": checkpoint_filename,
        "lora_resources": lora_resources,
        "upscaler_filename": upscaler_filename,
        "clip_skip": clip_skip,
    }


def _build_common_nodes(workflow: dict, params: dict) -> tuple:
    """
    Build common nodes shared by all workflows: checkpoint, LoRA chain, clip_skip.

    Returns:
        Tuple of (model_source, clip_source, vae_source)
    """
    # Node 1: CheckpointLoaderSimple
    workflow["1"] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": params["checkpoint_filename"],
        },
    }

    model_source = ["1", 0]
    clip_source = ["1", 1]
    vae_source = ["1", 2]

    # Insert LoRA loaders (chained), starting at node 10
    lora_node_id = 10
    for lora in params["lora_resources"]:
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
        model_source = [node_id, 0]
        clip_source = [node_id, 1]
        lora_node_id += 1

    # Node 8: CLIPSetLastLayer (if clip_skip is specified)
    clip_skip = params["clip_skip"]
    if clip_skip is not None:
        clip_skip_val = int(clip_skip)
        if clip_skip_val > 0:
            clip_skip_val = -clip_skip_val  # ComfyUI uses negative values
        workflow["8"] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {
                "clip": clip_source,
                "stop_at_clip_layer": clip_skip_val,
            },
        }
        clip_source = ["8", 0]

    return model_source, clip_source, vae_source


def _build_txt2img_workflow(metadata: dict, resources: dict) -> dict:
    """
    Build a standard txt2img ComfyUI workflow with optional LoRA(s).
    """
    params = _extract_common_params(metadata, resources)
    width = metadata.get("size", {}).get("width", 512)
    height = metadata.get("size", {}).get("height", 512)

    workflow = {}
    model_source, clip_source, vae_source = _build_common_nodes(workflow, params)

    # Node 2: CLIPTextEncode (positive prompt)
    workflow["2"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": params["prompt_text"],
            "clip": clip_source,
        },
    }

    # Node 3: CLIPTextEncode (negative prompt)
    workflow["3"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": params["negative_prompt"],
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
            "seed": params["seed"],
            "steps": params["steps"],
            "cfg": params["cfg_scale"],
            "sampler_name": params["sampler_name"],
            "scheduler": params["scheduler"],
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


def _build_hires_workflow(metadata: dict, resources: dict) -> dict:
    """
    Build a hires fix (txt2img-hires) ComfyUI workflow.

    Two-pass generation:
      Pass 1: Generate at base resolution (denoise=1.0)
      Upscale: Decode → upscale with model → scale to target → encode
      Pass 2: Refine at target resolution (denoise from metadata)

    Falls back to LatentUpscale if no upscaler model is available.
    """
    params = _extract_common_params(metadata, resources)
    hires_denoise = metadata.get("denoise") or 0.4

    base_size = metadata.get("base_size", metadata.get("size", {}))
    final_size = metadata.get("size", {})
    base_width = base_size.get("width", 512)
    base_height = base_size.get("height", 512)
    final_width = final_size.get("width", base_width)
    final_height = final_size.get("height", base_height)

    workflow = {}
    model_source, clip_source, vae_source = _build_common_nodes(workflow, params)

    # Node 2: CLIPTextEncode (positive prompt)
    workflow["2"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": params["prompt_text"],
            "clip": clip_source,
        },
    }

    # Node 3: CLIPTextEncode (negative prompt)
    workflow["3"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": params["negative_prompt"],
            "clip": clip_source,
        },
    }

    # Node 4: EmptyLatentImage (BASE size)
    workflow["4"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "width": base_width,
            "height": base_height,
        },
    }

    # Node 5: KSampler pass 1 (full generation)
    workflow["5"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_source,
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["4", 0],
            "seed": params["seed"],
            "steps": params["steps"],
            "cfg": params["cfg_scale"],
            "sampler_name": params["sampler_name"],
            "scheduler": params["scheduler"],
            "denoise": 1.0,
        },
    }

    # --- Upscale path ---
    upscaler_filename = params["upscaler_filename"]
    if upscaler_filename:
        # Model-based upscale: VAEDecode → UpscaleModel → ImageScale → VAEEncode

        # Node 20: VAEDecode (pass 1 output → image)
        workflow["20"] = {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": vae_source,
            },
        }

        # Node 21: UpscaleModelLoader
        workflow["21"] = {
            "class_type": "UpscaleModelLoader",
            "inputs": {
                "model_name": upscaler_filename,
            },
        }

        # Node 22: ImageUpscaleWithModel
        workflow["22"] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["21", 0],
                "image": ["20", 0],
            },
        }

        # Node 23: ImageScale (resize to exact target dimensions)
        workflow["23"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["22", 0],
                "upscale_method": "lanczos",
                "width": final_width,
                "height": final_height,
                "crop": "disabled",
            },
        }

        # Node 24: VAEEncode (image → latent for pass 2)
        workflow["24"] = {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["23", 0],
                "vae": vae_source,
            },
        }

        pass2_latent_source = ["24", 0]
    else:
        # Fallback: LatentUpscale (no upscaler model needed)
        workflow["20"] = {
            "class_type": "LatentUpscale",
            "inputs": {
                "samples": ["5", 0],
                "upscale_method": "bislerp",
                "width": final_width,
                "height": final_height,
                "crop": "disabled",
            },
        }

        pass2_latent_source = ["20", 0]

    # Node 25: KSampler pass 2 (refinement at target resolution)
    workflow["25"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_source,
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": pass2_latent_source,
            "seed": params["seed"],
            "steps": params["steps"],
            "cfg": params["cfg_scale"],
            "sampler_name": params["sampler_name"],
            "scheduler": params["scheduler"],
            "denoise": hires_denoise,
        },
    }

    # Node 6: VAEDecode (final)
    workflow["6"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["25", 0],
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

    if "25" in workflow:
        hires_node = workflow["25"]["inputs"]
        print(f"Hires fix: denoise={hires_node.get('denoise')}")

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
