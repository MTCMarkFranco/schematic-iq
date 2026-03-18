"""
Stage 3 prompt assembly — builds the complete prompt context for agent extraction.

Assembles image, IR (geometry + discovery), policy pack, and rule files
into the complete input for the Stage 3 agent.
"""

import os
from pathlib import Path

from services.prompts.loader import load_stage3_prompts, load_rule_files


def assemble_agent_context(
    geometry: dict,
    discovery: dict,
    wire_map: str,
    image_filename: str,
    prompt_version: str = "v1",
) -> dict:
    """Assemble the complete context for Stage 3 agent execution.

    Returns a dict with keys:
        - 'system_instructions': Full system prompt with policy pack
        - 'rule_files': List of (filename, content) tuples
        - 'wire_map': Formatted wire map text
        - 'geometry': Stage 1 geometry dict
        - 'discovery': Stage 2 discovery dict
        - 'image_filename': Name of the image file
    """
    prompts = load_stage3_prompts(version=prompt_version)

    # Build full system instructions
    parts = [prompts["system"]]
    if "policy_pack" in prompts:
        parts.append(prompts["policy_pack"])
    if "json_rules" in prompts:
        parts.append(prompts["json_rules"])
    system_instructions = "\n\n---\n\n".join(parts)

    return {
        "system_instructions": system_instructions,
        "rule_files": load_rule_files(),
        "wire_map": wire_map,
        "geometry": geometry,
        "discovery": discovery,
        "image_filename": image_filename,
    }
