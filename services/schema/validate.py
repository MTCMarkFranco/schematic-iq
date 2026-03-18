"""
JSON Schema validation for Schematic-IQ extraction outputs.

Validates final extraction output against the defined JSON Schema.
"""

import json
import os
from pathlib import Path

import jsonschema


_SCHEMA_DIR = Path(__file__).parent
_SCHEMA_CACHE: dict[str, dict] = {}


def _load_schema(schema_name: str = "final_output") -> dict:
    """Load and cache a JSON Schema."""
    if schema_name not in _SCHEMA_CACHE:
        schema_path = _SCHEMA_DIR / f"{schema_name}.schema.json"
        with open(schema_path) as f:
            _SCHEMA_CACHE[schema_name] = json.load(f)
    return _SCHEMA_CACHE[schema_name]


def validate_final_output(data: dict) -> tuple[bool, list[str]]:
    """Validate a final extraction output against the JSON Schema.

    Args:
        data: The extraction output dict to validate.

    Returns:
        Tuple of (is_valid, error_messages).
        If valid, error_messages is empty.
    """
    schema = _load_schema("final_output")
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if not errors:
        return True, []

    messages = []
    for error in errors:
        path = ".".join(str(p) for p in error.absolute_path)
        if path:
            messages.append(f"{path}: {error.message}")
        else:
            messages.append(error.message)

    return False, messages


def validate_file(filepath: str) -> tuple[bool, list[str]]:
    """Validate a JSON file against the final output schema.

    Args:
        filepath: Path to the JSON file.

    Returns:
        Tuple of (is_valid, error_messages).
    """
    with open(filepath) as f:
        data = json.load(f)
    return validate_final_output(data)
