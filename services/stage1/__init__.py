"""
Schematic-IQ Stage 1 — OpenCV Geometry Extraction Module.

This module provides a clean boundary for Stage 1 operations.
All logic delegates to the original geometry_extraction_service
to ensure zero behavioral change.
"""

from services.geometry_extraction_service import (
    extract_geometry,
    format_wire_map,
)

__all__ = ["extract_geometry", "format_wire_map"]
