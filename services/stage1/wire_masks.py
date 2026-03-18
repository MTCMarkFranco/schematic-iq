"""
Stage 1 wire masks — morphological wire extraction.

Re-exports from geometry_extraction_service for clean module access.
"""

from services.geometry_extraction_service import (
    extract_wire_mask,
)

__all__ = ["extract_wire_mask"]
