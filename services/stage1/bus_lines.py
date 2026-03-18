"""
Stage 1 bus lines — cable routing and bus line analysis.

Re-exports from geometry_extraction_service for clean module access.
"""

from services.geometry_extraction_service import (
    compute_cable_routing_map,
    analyze_terminal_wires,
)

__all__ = [
    "compute_cable_routing_map",
    "analyze_terminal_wires",
]
