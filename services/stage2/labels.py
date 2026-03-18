"""
Stage 2 label utilities — wire labels, partition labels, and label normalization.
"""

import re


def get_wire_labels(discovery: dict) -> list[str]:
    """Extract wire labels from discovery output."""
    return discovery.get("wire_labels", [])


def get_partition_labels(discovery: dict) -> list[str]:
    """Extract partition labels from discovery output."""
    return discovery.get("partition_labels", [])


def normalize_cable_label(label: str) -> str:
    """Normalize a cable label (remove spaces, standardize format)."""
    return re.sub(r"\s+", "", label.strip())
