# Stage 3 — Agentic Extraction (Foundry Agent + Code Interpreter)

## Overview

Stage 3 is where Schematic-IQ achieves 95–99% accuracy by deploying an Azure AI Foundry Agent with Code Interpreter that writes and executes custom OpenCV code against the actual image pixels.

## Module Structure

```
services/stage3/
├── __init__.py      # Main exports: Stage3Executor, DefaultAgenticExecutor
├── executor.py      # Executor interface + default implementation
└── prompting.py     # Prompt assembly (system + policy pack + rules)
```

## Executor Interface

```python
from services.stage3 import Stage3Executor, DefaultAgenticExecutor

# Use the default (current production path)
executor = DefaultAgenticExecutor()
result, elapsed = executor.execute(
    image_path="path/to/image.png",
    geometry=geometry_dict,
    discovery=discovery_dict,
    wire_map=wire_map_text,
    console=console,
    foundry_service=foundry,
    output_path="output/final.json",
)
```

## Future Executors

The `Stage3Executor` interface enables alternate execution strategies:

| Executor | Description | Status |
|----------|-------------|--------|
| `DefaultAgenticExecutor` | Foundry Agent + Code Interpreter | **Active** |
| `ReplayExecutor` | Replay from saved artifacts | Planned (Commit 9) |
| `CachedExecutor` | Cache-backed execution | Future |
| `LocalExecutor` | Local model execution | Future |

## Prompt Assembly

The `prompting.py` module assembles the full agent context:
1. System instructions (from versioned prompts)
2. Policy pack (deterministic rules)
3. JSON output rules (shared)
4. Domain rule files (15+ files from `prompts/rules/`)
5. Stage 1 geometry + Stage 2 discovery
6. Wire map text
