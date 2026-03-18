# Test Cases

## Overview

Schematic-IQ has targeted unit tests for the hardest problems in schematic extraction: junction ambiguity, crossover detection, and bus line taps.

## Test Categories

### Junction Tests (`services/stage1/tests/test_junctions.py`)

| Test | Description |
|------|-------------|
| Single wire chain | A single wire forms a chain |
| Connected wires | Two meeting wires form one chain |
| Disconnected wires | Distant wires form separate chains |
| T-junction | Three wires meeting at a T form one chain |
| Four-way junction | Four wires at a cross form one chain |
| Near miss | Close but not touching wires stay separate |
| Sequential chain IDs | Chain IDs are 0-indexed sequential |

### Crossover Tests (`services/stage1/tests/test_crossovers.py`)

| Test | Description |
|------|-------------|
| Perpendicular crossing | Two perpendicular wires meeting form one chain |
| Parallel non-touching | Parallel non-touching wires stay separate |
| Two bus lines | Wires crossing dual bus lines connect |
| Wire taps into bus | Horizontal wire meeting vertical bus connects |
| Multiple bus taps | Multiple wires tapping same bus connect |
| Wire stops at bus | Wire ending at bus connects |
| Wire crosses bus | Wire passing through bus connects |

### Wire Mask Tests (`services/stage1/tests/test_junctions.py`)

| Test | Description |
|------|-------------|
| Horizontal wire | Horizontal line produces wire mask content |
| Vertical wire | Vertical line produces wire mask content |
| Empty image | Empty image produces no wire mask |

### IR Validation Tests (`services/stage1/tests/test_junctions.py`)

| Test | Description |
|------|-------------|
| Valid Stage1 | Valid IR passes validation |
| Count mismatch | Summary/actual count mismatches detected |
| Invalid wire index | Out-of-range chain indices detected |

## Running Tests

```bash
# Run all unit tests
pytest -q

# Run junction tests only
pytest services/stage1/tests/test_junctions.py -v

# Run crossover tests only
pytest services/stage1/tests/test_crossovers.py -v

# Run with coverage
pytest --cov=services -q
```

## Micro-Fixtures (`test-data/micro/`)

Small synthetic crops for targeted testing. Currently tests use programmatically generated images via NumPy/OpenCV.
