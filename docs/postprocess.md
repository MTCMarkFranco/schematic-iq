# Post-Processing & Normalization

## Overview

The post-processing module provides deterministic JSON normalization for stable diffs, comparison, and golden file management.

## Normalizer (`services/postprocess/normalize.py`)

### Functions

| Function | Description |
|----------|-------------|
| `normalize(data, strip_volatile=False)` | Sort arrays, alphabetize keys |
| `canonicalize_ids(data)` | Re-number OBJ/C IDs sequentially |
| `normalize_for_diff(data)` | Full normalization for stable diffing |

### Usage

```python
from services.postprocess.normalize import normalize, canonicalize_ids, normalize_for_diff

# Basic normalization (sort arrays, alphabetize keys)
normalized = normalize(data)

# Strip volatile fields (timestamps, run IDs) for comparison
diff_ready = normalize_for_diff(data)

# Full canonicalization (re-number IDs for cross-run comparison)
canonical = canonicalize_ids(normalize(data))
```

### How It Works

1. **Array sorting**: Arrays of objects are sorted by stable keys (`system_object_id`, `connection_id`, `label`, etc.)
2. **Key ordering**: Dict keys are alphabetized for consistent serialization
3. **Volatile stripping**: Nondeterministic fields (`timestamp`, `run_id`, `elapsed`) removed during comparison
4. **ID canonicalization**: OBJ/C IDs renumbered sequentially so order-independent comparison works

### Integration with Golden Tests

The `services/testing/golden.py` module uses the normalizer for golden file comparison, ensuring that:
- Array ordering differences don't cause false failures
- Volatile fields don't affect comparison
- Output format is consistent and diff-friendly
