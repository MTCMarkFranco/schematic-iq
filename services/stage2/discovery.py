"""
Stage 2 discovery — core LLM-based discovery functions.

Re-exports from discovery_service for clean module access.
"""

from services.discovery_service import (
    run_discovery,
    run_full_discovery,
)

__all__ = ["run_discovery", "run_full_discovery"]
