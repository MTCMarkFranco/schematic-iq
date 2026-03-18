"""
Schematic-IQ Stage 2 — Diagram Discovery Module.

This module provides a clean boundary for Stage 2 operations.
All logic delegates to the original discovery_service to ensure
zero behavioral change.
"""

from services.discovery_service import (
    run_full_discovery,
    run_discovery,
    build_wire_map_supplements,
)

__all__ = ["run_full_discovery", "run_discovery", "build_wire_map_supplements"]
