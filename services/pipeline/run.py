"""
Pipeline runner — dispatches to the appropriate mode.

Currently only ``v1`` is implemented, which delegates directly to the
original ``main.py`` stage functions.  Adding a ``v2`` mode later only
requires a new branch in ``run_pipeline``.
"""

from __future__ import annotations

import base64
import os
import time
from datetime import datetime
from typing import TYPE_CHECKING

from services.telemetry import get_logger, PipelineMetrics

from .modes import PipelineMode, CURRENT_MODE

if TYPE_CHECKING:
    from rich.console import Console
    from services.foundry_service import FoundryService


def run_pipeline(
    image_path: str,
    foundry: "FoundryService",
    console: "Console",
    *,
    mode: PipelineMode = CURRENT_MODE,
    timestamp: str | None = None,
) -> dict:
    """Execute the full extraction pipeline under *mode*.

    Parameters
    ----------
    image_path : str
        Path to the schematic image.
    foundry : FoundryService
        Authenticated Foundry service instance.
    console : Console
        Rich console for user-facing output.
    mode : PipelineMode
        Which pipeline version to execute (default ``v1``).
    timestamp : str | None
        Override timestamp for output filenames.

    Returns
    -------
    dict
        Final extraction result (same shape regardless of mode).
    """
    log = get_logger("pipeline.run")

    if mode == PipelineMode.V1:
        return _run_v1(image_path, foundry, console, timestamp=timestamp)
    else:
        raise ValueError(f"Unsupported pipeline mode: {mode!r}")


# ── V1 implementation (delegates to existing stage functions) ────────────────

def _run_v1(
    image_path: str,
    foundry: "FoundryService",
    console: "Console",
    *,
    timestamp: str | None = None,
) -> dict:
    """V1 pipeline — identical to the original main.py flow."""
    from services.geometry_extraction_service import extract_geometry, format_wire_map
    from services.discovery_service import run_full_discovery
    from services.agent_extraction_service import run_agent_extraction
    from services.validation_service import post_process_and_validate

    log = get_logger("pipeline.v1")
    metrics = PipelineMetrics()
    ts = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    img_prefix = os.path.splitext(os.path.basename(image_path))[0]

    # Load image
    with open(image_path, "rb") as f:
        image_data_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Stage 1
    stage1_path = os.path.join("output", f"{img_prefix}-out-{ts}-stage1-geometry.json")
    with metrics.stage("stage1"):
        geometry = extract_geometry(image_path, output_path=stage1_path)
        wire_map = format_wire_map(geometry)
    log.info("stage1_done", elapsed=round(metrics.get_elapsed("stage1"), 3))

    # Stage 2
    stage2_path = os.path.join("output", f"{img_prefix}-out-{ts}-stage2-discovery.json")
    with metrics.stage("stage2"):
        discovery, wire_map, _ = run_full_discovery(
            client=foundry.get_openai_client(),
            image_data_b64=image_data_b64,
            image_path=image_path,
            geometry=geometry,
            wire_map=wire_map,
            console=console,
            output_path=stage2_path,
        )
    log.info("stage2_done", elapsed=round(metrics.get_elapsed("stage2"), 3))

    # Stage 3
    with metrics.stage("stage3"):
        parsed, elapsed_s3 = run_agent_extraction(
            image_path, geometry, discovery, wire_map, console, foundry
        )
    out_path = os.path.join("output", f"{img_prefix}-out-{ts}-stage3-final.json")
    parsed = post_process_and_validate(
        parsed, geometry, discovery, console, elapsed=elapsed_s3, output_path=out_path
    )
    log.info("stage3_done", elapsed=round(metrics.get_elapsed("stage3"), 3))

    log.info("pipeline_done", **metrics.summary())
    return parsed
