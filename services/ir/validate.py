"""
IR validation — lightweight invariant checks on Stage 1 and Stage 2 outputs.
"""

from services.ir.stage1 import Stage1Output
from services.ir.stage2 import Stage2Output


def validate_stage1(ir: Stage1Output) -> list[str]:
    """Validate Stage 1 IR invariants. Returns list of issues (empty = valid)."""
    issues = []

    # Image must have positive dimensions
    if ir.image_size.width <= 0 or ir.image_size.height <= 0:
        issues.append(f"Invalid image size: {ir.image_size.width}x{ir.image_size.height}")

    # Scale must be positive
    if ir.scale <= 0:
        issues.append(f"Invalid scale: {ir.scale}")

    # Summary counts should match actual data
    if ir.summary.wires != len(ir.wires):
        issues.append(f"Wire count mismatch: summary={ir.summary.wires}, actual={len(ir.wires)}")
    if ir.summary.wire_chains != len(ir.wire_chains):
        issues.append(f"Chain count mismatch: summary={ir.summary.wire_chains}, actual={len(ir.wire_chains)}")
    if ir.summary.dashed_regions != len(ir.dashed_regions):
        issues.append(f"Dashed region count mismatch: summary={ir.summary.dashed_regions}, actual={len(ir.dashed_regions)}")
    if ir.summary.slider_terminals != len(ir.slider_rects):
        issues.append(f"Slider count mismatch: summary={ir.summary.slider_terminals}, actual={len(ir.slider_rects)}")

    # Wire segments should have non-negative lengths
    for i, w in enumerate(ir.wires):
        if w.length < 0:
            issues.append(f"Wire {i}: negative length {w.length}")

    # Wire chain IDs should be unique
    chain_ids = [c.chain_id for c in ir.wire_chains]
    if len(chain_ids) != len(set(chain_ids)):
        issues.append("Duplicate chain IDs detected")

    # Wire indices in chains should reference valid wires
    n_wires = len(ir.wires)
    for chain in ir.wire_chains:
        for idx in chain.wire_indices:
            if idx < 0 or idx >= n_wires:
                issues.append(f"Chain {chain.chain_id}: invalid wire index {idx} (max {n_wires - 1})")

    return issues


def validate_stage2(ir: Stage2Output) -> list[str]:
    """Validate Stage 2 IR invariants. Returns list of issues (empty = valid)."""
    issues = []

    # All cables should have labels
    for i, cable in enumerate(ir.cables):
        if not cable.label.strip():
            issues.append(f"Cable {i}: empty label")

    # All terminals should have labels
    for i, terminal in enumerate(ir.terminals):
        if not terminal.label.strip():
            issues.append(f"Terminal {i}: empty label")

    # Terminal labels should be unique
    term_labels = [t.label for t in ir.terminals]
    dupes = [l for l in term_labels if term_labels.count(l) > 1]
    if dupes:
        issues.append(f"Duplicate terminal labels: {set(dupes)}")

    # Cable labels should be unique (after normalization)
    cable_labels = [c.label for c in ir.cables]
    dupes = [l for l in cable_labels if cable_labels.count(l) > 1]
    if dupes:
        issues.append(f"Duplicate cable labels: {set(dupes)}")

    return issues
