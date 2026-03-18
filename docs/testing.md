# Testing & Regression

## Overview

Schematic-IQ uses a golden-output regression harness to protect the 95–99% extraction accuracy path.

## Quick Start

```bash
# Create golden files from current outputs
python scripts/run_regression.py --update-golden

# Run smoke regression (non-strict: allows value-level diffs)
python scripts/run_regression.py --suite smoke

# Run strict regression (byte-for-byte match after normalization)
python scripts/run_regression.py --suite smoke --strict
```

## Architecture

### Golden Files (`test-data/golden/`)

Golden files are normalized JSON snapshots of known-good pipeline outputs. They serve as the regression baseline.

- Created via `--update-golden` from the `output/` directory
- Normalized: arrays sorted by stable keys, keys alphabetized
- Compared against new outputs using structural diffing

### Fixtures (`test-data/fixtures/`)

Small representative schematic images for automated testing. Place 2–5 images here for the smoke suite.

### Test Suites

| Suite | Description | Requires API? |
|-------|-------------|---------------|
| `smoke` | Compare existing outputs against golden files | No |

## Adding New Fixtures

1. Place the schematic image in `test-data/fixtures/`
2. Run the pipeline: `python main.py test-data/fixtures/my-image.png`
3. Update golden files: `python scripts/run_regression.py --update-golden`
4. Verify: `python scripts/run_regression.py --suite smoke --strict`

## Module Reference

- `services/testing/golden.py` — Normalization, comparison, fixture loading
- `services/testing/snapshot.py` — Snapshot writer for golden file creation
- `scripts/run_regression.py` — CLI regression runner
