# Pipeline Compatibility Modes

## Overview

The pipeline supports versioned execution modes, allowing future improvements
to coexist with the current behaviour behind a simple switch.

## Available Modes

| Mode | Description | Status |
|---|---|---|
| `v1` | Current 3-stage pipeline (OpenCV → LLM → Agent) | **Default** |

## Selecting a Mode

```bash
# Via CLI flag
python main.py image.png --pipeline-mode=v1

# Via environment variable
SIQ_PIPELINE_MODE=v1 python main.py image.png
```

CLI flag takes precedence over the environment variable.

## Programmatic Usage

```python
from services.pipeline import run_pipeline, PipelineMode

result = run_pipeline(
    image_path="test.png",
    foundry=foundry_service,
    console=console,
    mode=PipelineMode.V1,
)
```

## Adding a New Mode

1. Add the mode value to `PipelineMode` enum in `services/pipeline/modes.py`
2. Add a `_run_v2()` function in `services/pipeline/run.py`
3. Update the dispatch in `run_pipeline()`
4. Add regression tests for the new mode
5. Keep `v1` as default until the new mode proves parity
