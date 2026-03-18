"""
Stage 3 Replay — save and restore execution artifacts for deterministic replay.

Enables:
  - Saving all Stage 3 artifacts (inputs, intermediate, final JSON) per run
  - Replaying a run without calling the model
  - Comparing replayed outputs for regression testing
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


RUNS_DIR = os.path.join("output", "runs")


def _ensure_run_dir(run_id: str) -> str:
    """Create and return the run directory path."""
    run_dir = os.path.join(RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def generate_run_id(image_path: str) -> str:
    """Generate a unique run ID from image name and timestamp."""
    img_name = os.path.splitext(os.path.basename(image_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{img_name}-{timestamp}"


def save_run_artifacts(
    run_id: str,
    image_path: str,
    geometry: dict,
    discovery: dict,
    wire_map: str,
    final_output: dict,
    agent_response_text: str | None = None,
) -> str:
    """Save all artifacts for a pipeline run.

    Args:
        run_id: Unique run identifier.
        image_path: Path to the original image.
        geometry: Stage 1 geometry dict.
        discovery: Stage 2 discovery dict.
        wire_map: Wire map text.
        final_output: Stage 3 final extraction dict.
        agent_response_text: Optional raw agent response text.

    Returns:
        Path to the run directory.
    """
    run_dir = _ensure_run_dir(run_id)

    # Save metadata
    metadata = {
        "run_id": run_id,
        "image_path": image_path,
        "image_name": os.path.basename(image_path),
        "timestamp": datetime.now().isoformat(),
    }
    _save_json(os.path.join(run_dir, "metadata.json"), metadata)

    # Save stage outputs
    _save_json(os.path.join(run_dir, "stage1-geometry.json"), geometry)
    _save_json(os.path.join(run_dir, "stage2-discovery.json"), discovery)
    _save_json(os.path.join(run_dir, "stage3-final.json"), final_output)

    # Save wire map text
    with open(os.path.join(run_dir, "wire-map.txt"), "w", encoding="utf-8") as f:
        f.write(wire_map)

    # Save raw agent response if provided
    if agent_response_text:
        with open(os.path.join(run_dir, "agent-response.txt"), "w", encoding="utf-8") as f:
            f.write(agent_response_text)

    return run_dir


def load_run_artifacts(run_id: str) -> dict:
    """Load all artifacts from a saved run.

    Args:
        run_id: The run ID (directory name under output/runs/).

    Returns:
        Dict with keys: metadata, geometry, discovery, wire_map, final_output,
        agent_response_text (optional).
    """
    run_dir = os.path.join(RUNS_DIR, run_id)
    if not os.path.isdir(run_dir):
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    artifacts = {}
    artifacts["metadata"] = _load_json(os.path.join(run_dir, "metadata.json"))
    artifacts["geometry"] = _load_json(os.path.join(run_dir, "stage1-geometry.json"))
    artifacts["discovery"] = _load_json(os.path.join(run_dir, "stage2-discovery.json"))
    artifacts["final_output"] = _load_json(os.path.join(run_dir, "stage3-final.json"))

    wire_map_path = os.path.join(run_dir, "wire-map.txt")
    if os.path.exists(wire_map_path):
        with open(wire_map_path, "r", encoding="utf-8") as f:
            artifacts["wire_map"] = f.read()

    agent_path = os.path.join(run_dir, "agent-response.txt")
    if os.path.exists(agent_path):
        with open(agent_path, "r", encoding="utf-8") as f:
            artifacts["agent_response_text"] = f.read()

    return artifacts


def replay_run(run_id: str) -> dict:
    """Replay a saved run — returns the final output without calling any model.

    This enables deterministic reproduction of previous runs.

    Args:
        run_id: The run ID to replay.

    Returns:
        The final extraction output dict.
    """
    artifacts = load_run_artifacts(run_id)
    return artifacts["final_output"]


def list_runs() -> list[dict]:
    """List all saved runs with basic metadata.

    Returns:
        List of metadata dicts, sorted by timestamp (newest first).
    """
    if not os.path.isdir(RUNS_DIR):
        return []

    runs = []
    for entry in os.listdir(RUNS_DIR):
        metadata_path = os.path.join(RUNS_DIR, entry, "metadata.json")
        if os.path.isfile(metadata_path):
            runs.append(_load_json(metadata_path))

    return sorted(runs, key=lambda r: r.get("timestamp", ""), reverse=True)


def _save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
