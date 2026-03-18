"""
Pipeline compatibility modes.

Allows selecting ``v1`` (current behaviour) vs future modes without
breaking existing workflows.  The mode is resolved from:

1. CLI flag ``--pipeline-mode=v1``
2. Environment variable ``SIQ_PIPELINE_MODE``
3. Default: ``v1``
"""

import os
from enum import Enum


class PipelineMode(Enum):
    """Supported pipeline execution modes."""

    V1 = "v1"      # Current 3-stage pipeline (default)
    # V2 = "v2"    # Placeholder for future mode


# Resolve once at import time from env; CLI can override later.
_env_mode = os.environ.get("SIQ_PIPELINE_MODE", "v1").lower()
CURRENT_MODE = PipelineMode(_env_mode) if _env_mode in {m.value for m in PipelineMode} else PipelineMode.V1
