# Intermediate Representations (IR)

## Overview

Schematic-IQ defines typed IR (Intermediate Representation) contracts for each pipeline stage. These provide:

- **Type safety** — Typed access to stage outputs via dataclasses
- **Validation** — Lightweight invariant checks on structural properties
- **Serialization** — Round-trip conversion between dicts and IR objects

## Stage 1 IR (`services/ir/stage1.py`)

| Type | Description |
|------|-------------|
| `ImageSize` | Width/height of the input image |
| `WireSegment` | Single detected wire segment (coordinates, length, angle, orientation) |
| `WireChain` | Group of connected wire segments |
| `DashedRegion` | Dashed-line partition boundary |
| `SliderRect` | Terminal rectangle with slider contact |
| `GeometrySummary` | Summary counts |
| `Stage1Output` | Complete Stage 1 result |

### Usage
```python
from services.ir.stage1 import Stage1Output

ir = Stage1Output.from_dict(geometry_dict)
print(ir.summary.wires, ir.image_size.width)
raw = ir.to_dict()  # Round-trip back to dict
```

## Stage 2 IR (`services/ir/stage2.py`)

| Type | Description |
|------|-------------|
| `Component` | Discovered schematic component |
| `Cable` | Cable label circle |
| `Terminal` | Terminal block entry |
| `Stage2Output` | Complete Stage 2 result |

### Usage
```python
from services.ir.stage2 import Stage2Output

ir = Stage2Output.from_dict(discovery_dict)
print(len(ir.terminals), ir.has_crossovers)
raw = ir.to_dict()  # Round-trip back to dict
```

## Validation (`services/ir/validate.py`)

```python
from services.ir.validate import validate_stage1, validate_stage2

issues = validate_stage1(stage1_ir)
issues = validate_stage2(stage2_ir)
# Empty list = valid
```

### Stage 1 Invariants
- Positive image dimensions and scale
- Summary counts match actual data counts
- Non-negative wire lengths
- Unique chain IDs
- Valid wire index references in chains

### Stage 2 Invariants
- Non-empty labels for cables and terminals
- Unique terminal labels
- Unique cable labels
