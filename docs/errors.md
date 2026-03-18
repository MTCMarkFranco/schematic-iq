# Error Taxonomy

## Error Hierarchy

All pipeline errors inherit from `PipelineError` and carry a typed `exit_code`:

| Exception | Exit Code | Description |
|---|---|---|
| `PipelineError` | 1 | Generic pipeline failure |
| `Stage1Error` | 10 | OpenCV geometry extraction failed |
| `Stage2Error` | 20 | LLM discovery failed or returned unusable output |
| `Stage3Error` | 30 | Agent extraction failed or returned unusable output |
| `SchemaError` | 40 | Final output failed JSON Schema validation |
| `ConfigError` | 50 | Configuration invalid or missing |

## Fail-Closed Behavior

When any stage raises a `PipelineError`:

1. The error is logged with structured telemetry
2. `main.py` prints a human-readable message
3. The process exits with the appropriate exit code

This makes it safe to use in CI/CD — a non-zero exit code signals failure.

## Usage

```python
from services.errors import Stage1Error

def extract_geometry(image_path, ...):
    if not os.path.isfile(image_path):
        raise Stage1Error(f"Image not found: {image_path}")
    ...
```

## Exit Code Reference

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic error |
| 10 | Stage 1 failure |
| 20 | Stage 2 failure |
| 30 | Stage 3 failure |
| 40 | Schema validation failure |
| 50 | Configuration error |
| 130 | User interrupt (Ctrl+C) |
