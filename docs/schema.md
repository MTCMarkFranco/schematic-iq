# JSON Schema

## Overview

Schematic-IQ uses JSON Schema (Draft 7) to validate the final extraction output. The schema defines the structure for objects, connections, and partition memberships.

## Schema Location

- `services/schema/final_output.schema.json` — The canonical schema

## Schema Version

Current version: **v1** (identified by `$id` in the schema file).

When the schema evolves:
1. Create a new schema file (e.g., `final_output.v2.schema.json`)
2. Update the `$id` field
3. Maintain backward compatibility where possible
4. Update the `validate.py` loader

## Validation API

```python
from services.schema.validate import validate_final_output, validate_file

# Validate a dict
ok, errors = validate_final_output(data)

# Validate a file
ok, errors = validate_file("output/my-output.json")
```

## Object Types

| Type | Visual Form | Required Fields |
|------|-------------|-----------------|
| `TERMINAL` | rectangle | system_object_id, raw_text, has_slider |
| `WIRE` | line | system_object_id, raw_text, route_segments |
| `CABLE_LABEL` | circle | system_object_id, raw_text, center, radius |
| `OFF_PAGE_CONNECTOR` | circle | system_object_id, raw_text |
| `SYMBOLIC_COMPONENT` | varies | system_object_id, raw_text |

## Relationship Types

| Type | Description |
|------|-------------|
| `DIRECT_WIRE` | Terminal-to-wire or terminal-to-terminal direct connection |
| `WIRE_TO_CABLE` | Wire connects to a cable label |
| `CABLE_TO_CONNECTOR` | Cable connects to an off-page connector |
| `JUMPER_SHORT` | Two terminals share a jumper connection |
| `PIN_OF` | Component pin relationship |
| `ANNOTATES` | Label annotation relationship |
