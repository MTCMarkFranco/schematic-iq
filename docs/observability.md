# Observability

## Structured Logging

The pipeline supports structured JSON-line logging via the `services.telemetry` module.

### Enabling

```bash
# Text format at INFO level
python main.py image.png --log-level=info

# JSON lines format
python main.py image.png --log-level=info --json-log
```

By default, logging is at `WARNING` level so the existing Rich output is unaffected.

### Log Events

| Event | Stage | Fields |
|---|---|---|
| `pipeline_start` | — | `image` |
| `stage1_done` | 1 | `elapsed`, `wires`, `wire_chains`, `dashed_regions` |
| `stage2_done` | 2 | `elapsed`, `components`, `cables`, `terminals` |
| `stage3_done` | 3 | `elapsed`, `objects`, `connections` |
| `pipeline_done` | — | full `summary` with timings and counts |

### JSON Line Example

```json
{"ts": "2025-01-15 10:23:45,123", "level": "INFO", "logger": "siq.pipeline", "msg": "stage1_done", "elapsed": 1.234, "wires": 42, "wire_chains": 8, "dashed_regions": 2}
```

## Per-Stage Metrics

`PipelineMetrics` collects timing and counts for each stage:

```python
from services.telemetry import PipelineMetrics

metrics = PipelineMetrics()
with metrics.stage("stage1"):
    run_stage_1(...)
metrics.set_counts("stage1", wires=42)
print(metrics.summary())
```

### Summary Format

```json
{
  "total_elapsed_s": 45.678,
  "stages": {
    "stage1": {"elapsed_s": 1.234, "counts": {"wires": 42, "wire_chains": 8}},
    "stage2": {"elapsed_s": 12.345, "counts": {"components": 15, "cables": 3}},
    "stage3": {"elapsed_s": 32.099, "counts": {"objects": 28, "connections": 35}}
  }
}
```

## Using in Custom Scripts

```python
from services.telemetry import get_logger, configure_logging

configure_logging(level="DEBUG", json_output=True)
log = get_logger("my_script")
log.info("step_done", items=10, elapsed=0.5)
```
