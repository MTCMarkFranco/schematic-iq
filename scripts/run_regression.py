#!/usr/bin/env python
"""
Regression test runner — compares pipeline outputs against golden files.

Usage:
    python scripts/run_regression.py --suite smoke
    python scripts/run_regression.py --suite smoke --strict
    python scripts/run_regression.py --update-golden
    python scripts/run_regression.py --help
"""

import argparse
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.testing.golden import (
    compare_outputs,
    list_fixtures,
    load_golden,
    normalize_for_comparison,
)
from services.testing.snapshot import update_golden_from_output


GOLDEN_DIR = os.path.join("test-data", "golden")
OUTPUT_DIR = "output"


def find_golden_pairs() -> list[tuple[str, str]]:
    """Find pairs of (output_file, golden_file) for comparison."""
    pairs = []
    if not os.path.isdir(GOLDEN_DIR):
        return pairs

    golden_files = {f for f in os.listdir(GOLDEN_DIR) if f.endswith(".json")}
    output_files = {f for f in os.listdir(OUTPUT_DIR) if f.endswith(".json")}

    # Match golden files to any output file with the same stage suffix
    for golden_name in sorted(golden_files):
        # Golden files are named like: <fixture>-<stage>.json
        # Find matching output files by stage suffix
        for output_name in sorted(output_files):
            # Match by stage suffix (stage1-geometry, stage2-discovery, stage3-final)
            for stage in ("stage1-geometry", "stage2-discovery", "stage3-final",
                          "stage0-geometry", "stage1-discovery", "stage2-agent"):
                if golden_name.endswith(f"{stage}.json") and output_name.endswith(f"{stage}.json"):
                    pairs.append((
                        os.path.join(OUTPUT_DIR, output_name),
                        os.path.join(GOLDEN_DIR, golden_name),
                    ))
    return pairs


def run_smoke_suite(strict: bool = False, log_level: str = "warning") -> bool:
    """Run the smoke regression suite.

    Compares existing output files against golden files.
    Does NOT re-run the pipeline (that requires API keys and images).

    Args:
        strict: If True, require byte-for-byte match after normalization.
        log_level: Logging verbosity.

    Returns:
        True if all comparisons pass.
    """
    pairs = find_golden_pairs()

    if not pairs:
        print("⚠  No golden/output pairs found.")
        print(f"   Golden dir: {GOLDEN_DIR}")
        print(f"   Output dir: {OUTPUT_DIR}")
        print()
        print("   To create golden files from current outputs:")
        print("     python scripts/run_regression.py --update-golden")
        return True  # No pairs = nothing to fail

    all_pass = True
    for output_path, golden_path in pairs:
        fixture_name = os.path.basename(golden_path)
        print(f"  Comparing: {fixture_name}")

        try:
            with open(output_path) as f:
                actual = json.load(f)
            golden = load_golden(golden_path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"    ✗ Error loading: {e}")
            all_pass = False
            continue

        diffs = compare_outputs(actual, golden)

        if not diffs:
            print(f"    ✔ PASS")
        else:
            if strict:
                print(f"    ✗ FAIL — {len(diffs)} differences:")
                for d in diffs[:10]:
                    print(f"      - {d}")
                if len(diffs) > 10:
                    print(f"      ... and {len(diffs) - 10} more")
                all_pass = False
            else:
                # Non-strict: just warn about structural differences
                structural = [d for d in diffs if "missing" in d or "extra" in d or "type mismatch" in d]
                if structural:
                    print(f"    ⚠ {len(structural)} structural differences (non-strict)")
                    for d in structural[:5]:
                        print(f"      - {d}")
                    all_pass = False
                else:
                    print(f"    ✔ PASS (with {len(diffs)} value-level diffs)")

    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description="Schematic-IQ regression test runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_regression.py --suite smoke
  python scripts/run_regression.py --suite smoke --strict
  python scripts/run_regression.py --update-golden
        """,
    )
    parser.add_argument(
        "--suite",
        choices=["smoke"],
        default="smoke",
        help="Test suite to run (default: smoke)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require exact match after normalization",
    )
    parser.add_argument(
        "--update-golden",
        action="store_true",
        help="Update golden files from current output directory",
    )
    parser.add_argument(
        "--log-level",
        default="warning",
        choices=["debug", "info", "warning", "error"],
        help="Log verbosity (default: warning)",
    )

    args = parser.parse_args()

    if args.update_golden:
        print("Updating golden files from output/...")
        created = update_golden_from_output()
        for path in created:
            print(f"  ✔ {path}")
        print(f"\n{len(created)} golden files created/updated.")
        return

    print(f"═══ Schematic-IQ Regression Suite: {args.suite} ═══\n")

    passed = run_smoke_suite(strict=args.strict, log_level=args.log_level)

    print()
    if passed:
        print("═══ RESULT: PASS ═══")
    else:
        print("═══ RESULT: FAIL ═══")
        sys.exit(1)


if __name__ == "__main__":
    main()
