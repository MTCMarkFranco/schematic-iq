"""
Stage 1 junctions — wire intersection and chain analysis.

Re-exports from geometry_extraction_service for clean module access.
"""

from services.geometry_extraction_service import (
    build_wire_chains,
    analyze_intersection_pixels,
    batch_analyze_intersections,
)

__all__ = [
    "build_wire_chains",
    "analyze_intersection_pixels",
    "batch_analyze_intersections",
]
