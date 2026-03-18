"""
Snapshot writer — captures pipeline outputs for golden-file creation.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from services.testing.golden import normalize_for_comparison


def save_snapshot(
    fixture_name: str,
    stage1_data: dict | None = None,
    stage2_data: dict | None = None,
    stage3_data: dict | None = None,
    output_dir: str = "test-data/golden",
) -> dict[str, str]:
    """Save pipeline stage outputs as golden snapshots.

    Returns a dict mapping stage names to file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    saved = {}

    for stage_name, data in [
        ("stage1-geometry", stage1_data),
        ("stage2-discovery", stage2_data),
        ("stage3-final", stage3_data),
    ]:
        if data is not None:
            normalized = normalize_for_comparison(data)
            filename = f"{fixture_name}-{stage_name}.json"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w") as f:
                json.dump(normalized, f, indent=2, sort_keys=True)
            saved[stage_name] = filepath

    return saved


def update_golden_from_output(output_dir: str = "output", golden_dir: str = "test-data/golden") -> list[str]:
    """Copy existing output files to golden directory (for bootstrapping).

    Returns list of paths created.
    """
    os.makedirs(golden_dir, exist_ok=True)
    created = []
    for filename in sorted(os.listdir(output_dir)):
        if not filename.endswith(".json"):
            continue
        src = os.path.join(output_dir, filename)
        dst = os.path.join(golden_dir, filename)
        with open(src) as f:
            data = json.load(f)
        normalized = normalize_for_comparison(data)
        with open(dst, "w") as f:
            json.dump(normalized, f, indent=2, sort_keys=True)
        created.append(dst)
    return created
