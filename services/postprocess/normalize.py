"""
Deterministic JSON normalization for stable diffs and comparison.

Provides normalization functions that:
  - Sort arrays by stable keys (system_object_id, connection_id, etc.)
  - Canonicalize IDs (optional)
  - Remove nondeterministic fields (timestamps) from comparison output
"""

import re
from copy import deepcopy


# Fields to strip during comparison (nondeterministic or volatile)
VOLATILE_FIELDS = {"timestamp", "run_id", "elapsed", "processing_time"}

# Stable sort keys for each array type
_SORT_KEY_PRIORITY = [
    "system_object_id",
    "connection_id",
    "partition_id",
    "member_object_id",
    "label",
    "raw_text",
    "chain_id",
]


def _get_sort_key(item) -> str:
    """Extract a stable sort key from a dict or primitive."""
    if isinstance(item, dict):
        for key in _SORT_KEY_PRIORITY:
            if key in item:
                val = item[key]
                # Numeric sort for IDs like OBJ1, C1
                match = re.match(r"^([A-Z]+)(\d+)$", str(val))
                if match:
                    return f"{match.group(1)}{int(match.group(2)):06d}"
                return str(val)
        # Fallback: sort by all keys
        return str(sorted(item.items()))
    return str(item)


def normalize(data: dict, strip_volatile: bool = False) -> dict:
    """Normalize a JSON dict for stable comparison and diffing.

    Args:
        data: The data to normalize.
        strip_volatile: If True, remove volatile/nondeterministic fields.

    Returns:
        Normalized copy of the data.
    """
    return _normalize_value(deepcopy(data), strip_volatile)


def _normalize_value(value, strip_volatile: bool):
    """Recursively normalize a value."""
    if isinstance(value, dict):
        result = {}
        for k in sorted(value.keys()):
            if strip_volatile and k in VOLATILE_FIELDS:
                continue
            result[k] = _normalize_value(value[k], strip_volatile)
        return result
    elif isinstance(value, list):
        normalized = [_normalize_value(v, strip_volatile) for v in value]
        # Sort lists of dicts by stable key
        if normalized and all(isinstance(v, dict) for v in normalized):
            normalized.sort(key=_get_sort_key)
        return normalized
    else:
        return value


def canonicalize_ids(data: dict) -> dict:
    """Re-number all IDs (OBJ1, OBJ2, ...; C1, C2, ...) sequentially.

    This makes outputs from different runs comparable even if the agent
    assigned IDs in a different order.

    Args:
        data: The extraction output to canonicalize.

    Returns:
        Copy with canonicalized IDs.
    """
    data = deepcopy(data)

    # Build ID mapping from objects
    obj_map = {}
    for i, obj in enumerate(data.get("objects", []), 1):
        old_id = obj.get("system_object_id", "")
        new_id = f"OBJ{i}"
        obj_map[old_id] = new_id
        obj["system_object_id"] = new_id

    # Build ID mapping from connections
    conn_map = {}
    for i, conn in enumerate(data.get("connections", []), 1):
        old_id = conn.get("connection_id", "")
        new_id = f"C{i}"
        conn_map[old_id] = new_id
        conn["connection_id"] = new_id

        # Remap object references
        if conn.get("source_object_id") in obj_map:
            conn["source_object_id"] = obj_map[conn["source_object_id"]]
        if conn.get("target_object_id") in obj_map:
            conn["target_object_id"] = obj_map[conn["target_object_id"]]

    # Remap partition memberships
    for pm in data.get("partition_memberships", []):
        if pm.get("member_object_id") in obj_map:
            pm["member_object_id"] = obj_map[pm["member_object_id"]]

    return data


def normalize_for_diff(data: dict) -> dict:
    """Full normalization pipeline for stable diffing.

    Applies: strip volatile fields → normalize → sort.
    Does NOT canonicalize IDs (use canonicalize_ids separately if needed).
    """
    return normalize(data, strip_volatile=True)
