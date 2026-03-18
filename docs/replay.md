# Replay Mode

## Overview

Replay mode allows Stage 3 to save and restore all execution artifacts, enabling deterministic reproduction of pipeline runs without calling the model.

## Usage

### Saving Artifacts (Automatic)

When the pipeline runs, artifacts are saved to `output/runs/<run_id>/`:

```
output/runs/schematic-section-1-20260318-140000/
├── metadata.json          # Run metadata (image, timestamp)
├── stage1-geometry.json   # Stage 1 output
├── stage2-discovery.json  # Stage 2 output
├── stage3-final.json      # Final extraction
├── wire-map.txt           # Wire map text
└── agent-response.txt     # Raw agent response (optional)
```

### Replaying a Run

```bash
# List all saved runs
python scripts/replay_run.py --list

# Replay a specific run (prints JSON to stdout)
python scripts/replay_run.py --run schematic-section-1-20260318-140000

# Replay and compare to golden file
python scripts/replay_run.py --run <id> --compare test-data/golden/expected.json

# Replay and save output
python scripts/replay_run.py --run <id> --output output/replayed.json
```

### Programmatic Usage

```python
from services.stage3.replay import save_run_artifacts, replay_run, list_runs

# Save after a pipeline run
run_id = save_run_artifacts(
    run_id="my-run-001",
    image_path="test-data/image.png",
    geometry=geometry,
    discovery=discovery,
    wire_map=wire_map,
    final_output=final,
)

# Replay without model calls
result = replay_run("my-run-001")

# List all runs
runs = list_runs()
```

## Git Configuration

The `output/runs/` directory is excluded from git via `.gitignore` to avoid bloating the repository with generated artifacts.
