"""
Stage 1 geometry — core extraction functions.

Re-exports from geometry_extraction_service for clean module access.
"""

from services.geometry_extraction_service import (
    extract_geometry,
    format_wire_map,
    load_and_preprocess,
    load_binary_image,
    extract_wire_mask,
    detect_wires,
    build_wire_chains,
    detect_dashed_regions,
    detect_slider_rects,
    detect_terminal_rects,
)

__all__ = [
    "extract_geometry",
    "format_wire_map",
    "load_and_preprocess",
    "load_binary_image",
    "extract_wire_mask",
    "detect_wires",
    "build_wire_chains",
    "detect_dashed_regions",
    "detect_slider_rects",
    "detect_terminal_rects",
]
