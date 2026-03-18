# Stage 1 — OpenCV Geometry Extraction

## Overview

Stage 1 performs deterministic computer vision using OpenCV to extract wire geometry, terminal positions, dashed partitions, and slider contacts from electrical schematic images.

## Module Structure

```
services/stage1/
├── __init__.py      # Main exports: extract_geometry, format_wire_map
├── geometry.py      # Core extraction functions
├── wire_masks.py    # Morphological wire extraction
├── junctions.py     # Wire intersection and chain analysis
└── bus_lines.py     # Cable routing and bus line analysis
```

## Usage

```python
from services.stage1 import extract_geometry, format_wire_map

geometry = extract_geometry("path/to/image.png", output_path="output/geo.json")
wire_map = format_wire_map(geometry)
```

## Functions

| Function | Module | Description |
|----------|--------|-------------|
| `extract_geometry()` | geometry | Main extraction pipeline |
| `format_wire_map()` | geometry | Format geometry as text for LLM |
| `extract_wire_mask()` | wire_masks | Morphological wire feature isolation |
| `detect_wires()` | geometry | Hough line wire detection |
| `build_wire_chains()` | junctions | Group segments into wire chains |
| `analyze_intersection_pixels()` | junctions | BEND/STRAIGHT/DOT analysis |
| `batch_analyze_intersections()` | junctions | Analyze wire against all bus lines |
| `compute_cable_routing_map()` | bus_lines | Cable circle detection + mapping |
| `analyze_terminal_wires()` | bus_lines | Terminal wire analysis + jumpers |

## Key Algorithms

- **Morphological wire extraction**: Long thin kernels isolate wire-like features
- **Hough Line Transform**: Sub-pixel wire segment detection
- **Collinear segment merging**: Joins fragmented wire pieces
- **Wire chain building**: Groups connected segments into paths
- **Intersection analysis**: Pixel-level BEND/STRAIGHT/DOT classification at bus line crossings
