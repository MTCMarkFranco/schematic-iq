"""Pipeline compatibility modes and versioned execution."""

from .modes import PipelineMode, CURRENT_MODE
from .run import run_pipeline

__all__ = ["PipelineMode", "CURRENT_MODE", "run_pipeline"]
