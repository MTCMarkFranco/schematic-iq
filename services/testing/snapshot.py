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
    """Promote output files to golden files.

    Output files are named ``<fixture>-out-<timestamp>-<stage>.json``.
    Golden files are written as ``golden-<fixture>-<stage>.json``.
    When multiple timestamps exist for the same fixture+stage, the latest
    output is used.

    Returns list of golden paths created.
    """
    import re

    output_re = re.compile(
        r"^(?P<fixture>.+?)-out-(?P<ts>\d{8}-\d{6})-(?P<stage>stage\d+-\w+)\.json$"
    )

    os.makedirs(golden_dir, exist_ok=True)

    # Pick the latest output per (fixture, stage)
    latest: dict[tuple[str, str], tuple[str, str]] = {}  # key -> (ts, filename)
    for filename in os.listdir(output_dir):
        m = output_re.match(filename)
        if not m:
            continue
        fixture, ts, stage = m.group("fixture"), m.group("ts"), m.group("stage")
        key = (fixture, stage)
        if key not in latest or ts > latest[key][0]:
            latest[key] = (ts, filename)

    created = []
    for (fixture, stage), (_ts, filename) in sorted(latest.items()):
        src = os.path.join(output_dir, filename)
        golden_name = f"golden-{fixture}-{stage}.json"
        dst = os.path.join(golden_dir, golden_name)
        with open(src) as f:
            data = json.load(f)
        normalized = normalize_for_comparison(data)
        with open(dst, "w") as f:
            json.dump(normalized, f, indent=2, sort_keys=True)
        created.append(dst)
    return created
