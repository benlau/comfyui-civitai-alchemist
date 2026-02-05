"""
Debug utilities for the pipeline.

Provides debug report collection, logging configuration,
and report serialization for --debug mode.

Two report files are produced:
  - debug_report.json      — compact summary (~15-25KB) for AI/human quick review
  - debug_report_full.json — complete data with raw API responses for deep investigation
"""

import copy
import json
import logging
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


logger = logging.getLogger("civitai_alchemist")


def configure_debug_logging():
    """Configure logging to output verbose info to stderr."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger("civitai_alchemist")
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)


def create_debug_report(image_url, args):
    """Create initial debug report structure with environment info."""
    try:
        import requests
        requests_version = requests.__version__
    except Exception:
        requests_version = "unknown"

    return {
        "debug_version": "1.0",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "input_url": image_url,
        "image_id": None,
        "args": {
            "output_dir": args.output_dir,
            "models_dir": args.models_dir,
        },
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
            "models_dir": None,
            "models_dir_exists": None,
            "api_key_present": False,
            "package_versions": {
                "requests": requests_version,
            },
        },
        "steps": {},
        "api_calls": [],
        "errors": [],
        "total_duration_ms": 0,
    }


def _build_summary(report):
    """
    Build a compact summary from the full debug report.

    Strips:
      - api_calls[].response_body (the biggest contributor to file size)
      - steps.fetch_metadata.raw_image_data (raw Civitai API response)
    Keeps everything else intact so the summary is self-contained for diagnosis.
    """
    summary = copy.deepcopy(report)

    # Strip response bodies from API calls — keep only the envelope
    for call in summary.get("api_calls", []):
        call.pop("response_body", None)

    # Strip raw_image_data from fetch_metadata step
    fetch_step = summary.get("steps", {}).get("fetch_metadata")
    if fetch_step:
        fetch_step.pop("raw_image_data", None)

    # Strip bulky raw_meta.comfy field (embedded ComfyUI workflow JSON string)
    result = (fetch_step or {}).get("result", {})
    raw_meta = result.get("raw_meta")
    if isinstance(raw_meta, dict) and "comfy" in raw_meta:
        raw_meta.pop("comfy")

    return summary


def save_debug_report(report, output_dir):
    """
    Save debug reports to the output directory.

    Produces two files:
      - debug_report.json      — compact summary for quick AI/human review
      - debug_report_full.json — complete data with raw API responses
    """
    output_dir = Path(output_dir)

    # Full report
    full_path = output_dir / "debug_report_full.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    # Summary report (stripped of large response bodies)
    summary = _build_summary(report)
    summary_path = output_dir / "debug_report.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nDebug report saved to {summary_path} (summary)", file=sys.stderr)
    print(f"Full debug report saved to {full_path}", file=sys.stderr)
