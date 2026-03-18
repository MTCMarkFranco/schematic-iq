"""
Golden-output comparison helpers.

Loads fixtures, normalizes JSON for stable diffing, and reports differences.
Uses the centralized normalizer from services.postprocess.normalize.
"""

import json
import os
from pathlib import Path
from typing import Any

from services.postprocess.normalize import normalize as _normalize


def _stable_sort_key(item: Any) -> str:
    """Produce a stable sort key for JSON objects."""
    if isinstance(item, dict):
        # Use system_object_id, connection_id, partition_id, label, or raw_text as key
        for key in ("system_object_id", "connection_id", "partition_id", "label", "raw_text"):
            if key in item:
                return str(item[key])
        return json.dumps(item, sort_keys=True)
    return str(item)


def normalize_for_comparison(data: dict) -> dict:
    """Normalize a JSON dict for stable comparison.

    - Sorts arrays of objects by stable keys
    - Removes volatile fields (timestamps, run IDs)
    - Preserves all semantic content

    Delegates to the centralized normalizer.
    """
    return _normalize(data, strip_volatile=True)


def load_golden(golden_path: str) -> dict:
    """Load a golden JSON file."""
    with open(golden_path, "r") as f:
        return json.load(f)


def save_golden(data: dict, golden_path: str) -> None:
    """Save data as a golden JSON file (normalized)."""
    os.makedirs(os.path.dirname(golden_path), exist_ok=True)
    normalized = normalize_for_comparison(data)
    with open(golden_path, "w") as f:
        json.dump(normalized, f, indent=2, sort_keys=True)


def compare_outputs(actual: dict, expected: dict) -> list[str]:
    """Compare two output dicts and return a list of difference descriptions.

    Returns empty list if outputs match (after normalization).
    """
    norm_actual = normalize_for_comparison(actual)
    norm_expected = normalize_for_comparison(expected)
    differences = []
    _diff_dicts("", norm_actual, norm_expected, differences)
    return differences


def _diff_dicts(path: str, actual: Any, expected: Any, diffs: list[str]) -> None:
    """Recursively diff two normalized structures."""
    if type(actual) != type(expected):
        diffs.append(f"{path}: type mismatch {type(actual).__name__} vs {type(expected).__name__}")
        return

    if isinstance(actual, dict):
        all_keys = set(actual.keys()) | set(expected.keys())
        for key in sorted(all_keys):
            child_path = f"{path}.{key}" if path else key
            if key not in actual:
                diffs.append(f"{child_path}: missing in actual")
            elif key not in expected:
                diffs.append(f"{child_path}: extra in actual")
            else:
                _diff_dicts(child_path, actual[key], expected[key], diffs)
    elif isinstance(actual, list):
        if len(actual) != len(expected):
            diffs.append(f"{path}: list length {len(actual)} vs {len(expected)}")
        for i, (a, e) in enumerate(zip(actual, expected)):
            _diff_dicts(f"{path}[{i}]", a, e, diffs)
    else:
        if actual != expected:
            diffs.append(f"{path}: {actual!r} != {expected!r}")


def list_fixtures(fixtures_dir: str) -> list[str]:
    """List image fixture files in a directory."""
    fixtures_dir = Path(fixtures_dir)
    if not fixtures_dir.exists():
        return []
    extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    return sorted(
        str(p) for p in fixtures_dir.iterdir() if p.suffix.lower() in extensions
    )
