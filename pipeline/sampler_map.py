"""
Sampler Mapping

Maps Civitai sampler/scheduler names to ComfyUI equivalents.

Civitai embeds both sampler and scheduler in a single string (e.g. "DPM++ 2M Karras"),
while ComfyUI separates them into sampler_name and scheduler.
"""

import logging

logger = logging.getLogger("civitai_alchemist.workflow")

# Civitai sampler name -> ComfyUI sampler name
# Note: scheduler suffixes ("Karras", "Exponential") are stripped before lookup
SAMPLER_MAP = {
    "Euler": "euler",
    "Euler a": "euler_ancestral",
    "Euler A": "euler_ancestral",
    "Heun": "heun",
    "Heun++": "heunpp2",
    "DPM2": "dpm_2",
    "DPM2 a": "dpm_2_ancestral",
    "LMS": "lms",
    "DPM fast": "dpm_fast",
    "DPM adaptive": "dpm_adaptive",
    "DPM++ SDE": "dpmpp_sde",
    "DPM++ 2S a": "dpmpp_2s_ancestral",
    "DPM++ 2M": "dpmpp_2m",
    "DPM++ 2M SDE": "dpmpp_2m_sde",
    "DPM++ 3M SDE": "dpmpp_3m_sde",
    "DDIM": "ddim",
    "PLMS": "euler",  # No direct PLMS in ComfyUI; closest fallback
    "UniPC": "uni_pc",
    "LCM": "lcm",
    "DDPM": "ddpm",
}

# Known scheduler suffixes in Civitai sampler names
SCHEDULER_SUFFIXES = {
    "Karras": "karras",
    "Exponential": "exponential",
}

# Civitai "Schedule type" field -> ComfyUI scheduler name
SCHEDULE_TYPE_MAP = {
    "Karras": "karras",
    "Exponential": "exponential",
    "Automatic": "normal",
    "Uniform": "sgm_uniform",
    "Normal": "normal",
    "Simple": "simple",
    "SGM Uniform": "sgm_uniform",
    "Beta": "beta",
}


def map_sampler(civitai_sampler: str, schedule_type: str = None) -> tuple[str, str]:
    """
    Map a Civitai sampler name to ComfyUI sampler_name and scheduler.

    Args:
        civitai_sampler: Sampler name from Civitai metadata (e.g. "DPM++ 2M Karras")
        schedule_type: Optional "Schedule type" field from Civitai metadata

    Returns:
        Tuple of (comfyui_sampler_name, comfyui_scheduler)
    """
    if not civitai_sampler:
        return ("euler", "normal")

    sampler_str = civitai_sampler.strip()
    scheduler = "normal"

    # Check for scheduler suffix and strip it
    for suffix, sched_name in SCHEDULER_SUFFIXES.items():
        if sampler_str.endswith(f" {suffix}"):
            sampler_str = sampler_str[: -(len(suffix) + 1)].strip()
            scheduler = sched_name
            break

    # Look up sampler
    comfyui_sampler = SAMPLER_MAP.get(sampler_str)

    if comfyui_sampler is None:
        # Try case-insensitive match
        for key, value in SAMPLER_MAP.items():
            if key.lower() == sampler_str.lower():
                comfyui_sampler = value
                break

    if comfyui_sampler is None:
        logger.debug("Unknown sampler '%s', falling back to 'euler'", civitai_sampler)
        print(f"Warning: Unknown sampler '{civitai_sampler}', falling back to 'euler'")
        comfyui_sampler = "euler"

    # Override scheduler if explicit "Schedule type" is provided
    if schedule_type:
        mapped = SCHEDULE_TYPE_MAP.get(schedule_type)
        if mapped:
            scheduler = mapped

    return (comfyui_sampler, scheduler)
