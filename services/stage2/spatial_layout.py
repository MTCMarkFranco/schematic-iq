"""
Stage 2 spatial layout — position and layout analysis.

Provides utilities for working with the spatial layout information
discovered by Stage 2 (component positions, cable positions, etc.).
"""

from services.ir.stage2 import Stage2Output


def get_component_positions(discovery: dict) -> dict[str, str]:
    """Extract component label -> position mapping."""
    return {
        c["label"]: c.get("position", "")
        for c in discovery.get("components", [])
        if isinstance(c, dict)
    }


def get_cable_positions(discovery: dict) -> dict[str, str]:
    """Extract cable label -> position mapping."""
    return {
        c["label"]: c.get("position", "")
        for c in discovery.get("cables", [])
        if isinstance(c, dict)
    }


def get_terminal_blocks(discovery: dict) -> dict[str, list[str]]:
    """Extract terminal block -> terminal labels mapping."""
    blocks: dict[str, list[str]] = {}
    for t in discovery.get("terminals", []):
        if isinstance(t, dict):
            block = t.get("terminal_block", "")
            if block:
                blocks.setdefault(block, []).append(t["label"])
    return blocks
