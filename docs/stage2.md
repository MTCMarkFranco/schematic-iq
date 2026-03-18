# Stage 2 — Diagram Discovery (LLM)

## Overview

Stage 2 runs multi-pass vision LLM scanning to catalog all visible elements in the schematic: components, cables, terminals, wire labels, and partition boundaries.

## Module Structure

```
services/stage2/
├── __init__.py           # Main exports: run_full_discovery
├── discovery.py          # Core LLM discovery functions
├── spatial_layout.py     # Position and layout utilities
├── cable_terminal_map.py # Cable-terminal relationship mapping
└── labels.py             # Wire label and partition utilities
```

## Usage

```python
from services.stage2 import run_full_discovery

discovery, wire_map, elapsed = run_full_discovery(
    client=openai_client,
    image_data_b64=base64_image,
    image_path="path/to/image.png",
    geometry=geometry_dict,
    wire_map=wire_map_text,
    console=console,
    output_path="output/discovery.json",
)
```

## Functions

| Function | Module | Description |
|----------|--------|-------------|
| `run_full_discovery()` | discovery | Full pipeline: multi-run discovery + supplements |
| `run_discovery()` | discovery | Raw multi-run LLM scan with union merge |
| `build_wire_map_supplements()` | __init__ | Compute cable routing + terminal wire supplements |
| `get_component_positions()` | spatial_layout | Component position mapping |
| `get_cable_positions()` | spatial_layout | Cable position mapping |
| `get_terminal_blocks()` | spatial_layout | Terminal block membership |
| `get_cable_terminal_map()` | cable_terminal_map | Cable-terminal relationships |
| `get_wire_labels()` | labels | Wire label extraction |
| `normalize_cable_label()` | labels | Cable label normalization |

## Strategy: Best-of-3 Union Merge

Stage 2 runs 3 independent scans (configurable via `DISCOVERY_RUNS` env var) and union-merges the results, deduplicating by label. This catches items any single run might miss.
